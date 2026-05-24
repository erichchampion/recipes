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


def split_recipes(locale_dir, recipe_map):
    source = locale_dir / 'recipes.json'
    data = json.loads(source.read_text(encoding='utf-8'))
    written = 0
    for recipe in data['@graph']:
        category_id = recipe_map.get(recipe['recipeCategory'])
        if category_id is None:
            category_id = slugify(recipe['recipeCategory'])
        out_path = locale_dir / 'recipes' / category_id / f"{recipe['identifier']}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(recipe, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        written += 1
    return written


def split_tips(locale_dir, tip_map):
    source = locale_dir / 'tips.json'
    data = json.loads(source.read_text(encoding='utf-8'))
    written = 0
    for tip in data:
        category_id = tip_map.get(tip['category'])
        if category_id is None:
            category_id = slugify(tip['category'])
        out_path = locale_dir / 'tips' / category_id / f"{tip['id']}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(tip, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        written += 1
    return written


def find_locales(root):
    return [
        d for d in sorted(root.iterdir())
        if d.is_dir() and (d / 'recipes.json').exists() and (d / 'tips.json').exists()
    ]


def main():
    recipe_map, tip_map = load_category_map(ROOT / 'categories.json')

    for locale_dir in find_locales(ROOT):
        locale = locale_dir.name
        recipes_written = split_recipes(locale_dir, recipe_map)
        tips_written = split_tips(locale_dir, tip_map)
        print(f"{locale}: {recipes_written} recipes, {tips_written} tips")


if __name__ == '__main__':
    main()
