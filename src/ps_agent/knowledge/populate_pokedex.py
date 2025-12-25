
import argparse
import json
import time
from pathlib import Path
from typing import List, Dict

import requests
from ps_agent.llm.llm_client import LLMClient
from ps_agent.utils.format import to_id
from ps_agent.utils.logger import get_logger

logger = get_logger(__name__)

POKEAPI_BASE = "https://pokeapi.co/api/v2/pokemon"
CACHE_DIR = Path("data/knowledge_cache")

def fetch_pokemon_data(species: str) -> Dict | None:
    # Try using species name AS IS first (essential for bulk mode where names come from PokeAPI)
    urls_to_try = [
        f"{POKEAPI_BASE}/{species}", # Try "shaymin-land"
        f"{POKEAPI_BASE}/{to_id(species)}", # Try "shayminland"
    ]
    
    # Heuristics for common failures
    species_id = to_id(species)
    if "chiyu" in species_id: urls_to_try.append(f"{POKEAPI_BASE}/chi-yu")
    elif "wochien" in species_id: urls_to_try.append(f"{POKEAPI_BASE}/wo-chien")
    elif "baopian" in species_id: urls_to_try.append(f"{POKEAPI_BASE}/chien-pao")
    elif "tinglu" in species_id: urls_to_try.append(f"{POKEAPI_BASE}/ting-lu")
    elif "fluttermane" in species_id: urls_to_try.append(f"{POKEAPI_BASE}/flutter-mane")
    elif "iron" in species_id: urls_to_try.append(f"{POKEAPI_BASE}/{species_id.replace('iron', 'iron-')}")
    elif "scream" in species_id: urls_to_try.append(f"{POKEAPI_BASE}/{species_id.replace('scream', 'scream-')}")
    elif "brute" in species_id: urls_to_try.append(f"{POKEAPI_BASE}/{species_id.replace('brute', 'brute-')}")
    elif "great" in species_id: urls_to_try.append(f"{POKEAPI_BASE}/{species_id.replace('great', 'great-')}")

    for url in urls_to_try:
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                stats = {s["stat"]["name"]: s["base_stat"] for s in data["stats"]}
                base_stats = {
                    "hp": stats["hp"],
                    "atk": stats["attack"],
                    "def": stats["defense"],
                    "spa": stats["special-attack"],
                    "spd": stats["special-defense"],
                    "spe": stats["speed"],
                }
                return {
                    "base_stats": base_stats,
                    "types": [t["type"]["name"] for t in data["types"]],
                    "abilities": [a["ability"]["name"] for a in data["abilities"]],
                    "weight_kg": data["weight"] / 10.0
                }
        except Exception:
            pass
            
    logger.warning("pokeapi_404", species=species)
    return None

def get_target_list_from_llm(count: int) -> List[str]:
    client = LLMClient()
    prompt = f"""
    List the top {count} most common or dangerous Pokemon in Gen 9 Random Battles.
    Return ONLY a JSON list of strings, e.g. ["Pikachu", "Charizard"].
    Do not add markdown formatting.
    """
    resp = client.chat([{"role": "user", "content": prompt}])
    try:
        # Strip markdown if present
        cleaned = resp.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("\n", 1)[0]
        return json.loads(cleaned)
    except Exception as e:
        logger.error("llm_list_failed", error=str(e))
        return []

def fetch_all_species_list() -> List[str]:
    """Fetch ALL pokemon species names from PokeAPI."""
    try:
        # Limit 2000 covers everything up to Gen 9 DLC
        url = f"{POKEAPI_BASE}?limit=2000"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return [entry["name"] for entry in data["results"]]
    except Exception as e:
        logger.error("pokeapi_list_failed", error=str(e))
        return []

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=50, help="Number of pokemon to suggest via LLM")
    parser.add_argument("--add", nargs="+", help="Manually add specific pokemon species")
    parser.add_argument("--all", action="store_true", help="Fetch ALL pokemon from PokeAPI (approx 1300+)")
    parser.add_argument("--cache-dir", default="data/knowledge_cache", help="Cache directory")
    args = parser.parse_args()
    
    cache_path = Path(args.cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    pokedex_file = cache_path / "pokedex.json"
    
    current_db = {}
    if pokedex_file.exists():
        with open(pokedex_file, "r") as f:
            current_db = json.load(f)
            
    targets = []
    if args.add:
        targets.extend(args.add)
    elif args.all:
        print("🌍 Fetching full species list from PokeAPI (this may take a while)...")
        targets.extend(fetch_all_species_list())
        print(f"🌍 Found {len(targets)} species.")
    else:
        print(f"🤖 Asking LLM for top {args.count} Random Battle threats...")
        targets.extend(get_target_list_from_llm(args.count))
        
    print(f"📋 Fetching data for {len(targets)} pokemon...")
    
    updated_count = 0
    # Process in chunks to save progress intermittently if list is huge
    for i, mon in enumerate(targets):
        mon_id = to_id(mon)
        if mon_id in current_db and not args.add:
            print(f"  [SKIP] {mon} (already cached)")
            continue
            
        print(f"  [FETCH] ({i+1}/{len(targets)}) {mon} ...")
        data = fetch_pokemon_data(mon)
        if data:
            current_db[mon_id] = data
            updated_count += 1
        
        # Save every 50 entries to avoid losing progress
        if updated_count > 0 and updated_count % 50 == 0:
             with open(pokedex_file, "w") as f:
                json.dump(current_db, f, indent=2)
             print("  (Progress saved)")

        time.sleep(0.2) # Be nice to PokeAPI
        
    with open(pokedex_file, "w") as f:
        json.dump(current_db, f, indent=2)
        
    print(f"✅ Done. Updated {updated_count} entries. Total: {len(current_db)}")

if __name__ == "__main__":
    main()

