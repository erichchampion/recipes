import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent


def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def load_category_map(categories_path):
    data = json.loads(categories_path.read_text(encoding='utf-8'))
    recipe_map = {entry['recipeCategory']: entry['id'] for entry in data['recipes']}
    tip_map = {entry['category']: entry['id'] for entry in data['tips']}
    return recipe_map, tip_map


def _prune_orphans(base_dir, expected_paths):
    """Delete .json files under base_dir not in expected_paths. Return list of removed paths."""
    if not base_dir.is_dir():
        return []
    removed = []
    for existing in base_dir.rglob('*.json'):
        if existing not in expected_paths:
            existing.unlink()
            removed.append(existing)
    # Clean up now-empty category directories
    for sub in sorted(base_dir.iterdir(), reverse=True):
        if sub.is_dir() and not any(sub.iterdir()):
            sub.rmdir()
    return removed


def split_recipes(locale_dir, recipe_map, delete_orphans=True):
    source = locale_dir / 'recipes.json'
    data = json.loads(source.read_text(encoding='utf-8'))
    expected = set()
    written = 0
    for recipe in data['@graph']:
        category_id = recipe_map.get(recipe['recipeCategory'])
        if category_id is None:
            category_id = slugify(recipe['recipeCategory'])
        out_path = locale_dir / 'recipes' / category_id / f"{recipe['identifier']}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(recipe, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        expected.add(out_path)
        written += 1
    removed = _prune_orphans(locale_dir / 'recipes', expected) if delete_orphans else []
    return written, removed


def split_tips(locale_dir, tip_map, delete_orphans=True):
    source = locale_dir / 'tips.json'
    data = json.loads(source.read_text(encoding='utf-8'))
    expected = set()
    written = 0
    for tip in data:
        category_id = tip_map.get(tip['category'])
        if category_id is None:
            category_id = slugify(tip['category'])
        out_path = locale_dir / 'tips' / category_id / f"{tip['id']}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(tip, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        expected.add(out_path)
        written += 1
    removed = _prune_orphans(locale_dir / 'tips', expected) if delete_orphans else []
    return written, removed


def find_locales(root):
    return [
        d for d in sorted(root.iterdir())
        if d.is_dir() and (d / 'recipes.json').exists() and (d / 'tips.json').exists()
    ]


def main():
    parser = argparse.ArgumentParser(
        description='Explode per-locale recipes.json and tips.json into split files.',
    )
    parser.add_argument(
        '--no-delete',
        action='store_true',
        help='Keep existing split files that have no entry in the combined input (default: delete).',
    )
    args = parser.parse_args()
    delete_orphans = not args.no_delete

    recipe_map, tip_map = load_category_map(ROOT / 'categories.json')

    for locale_dir in find_locales(ROOT):
        locale = locale_dir.name
        recipes_written, recipes_removed = split_recipes(locale_dir, recipe_map, delete_orphans)
        tips_written, tips_removed = split_tips(locale_dir, tip_map, delete_orphans)
        suffix = ''
        if recipes_removed or tips_removed:
            suffix = f" (removed {len(recipes_removed)} recipe, {len(tips_removed)} tip orphan(s))"
        print(f"{locale}: {recipes_written} recipes, {tips_written} tips{suffix}")
        for path in recipes_removed + tips_removed:
            print(f"  - removed {path.relative_to(ROOT)}")


if __name__ == '__main__':
    main()
