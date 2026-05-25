import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

def main():
    recipes_path = ROOT / 'en' / 'recipes.json'
    tips_path = ROOT / 'en' / 'tips.json'
    categories_path = ROOT / 'categories.json'

    for path in (recipes_path, tips_path):
        if not path.exists():
            print(
                f"Error: {path.relative_to(ROOT)} not found. "
                f"Run `python scripts/combine-json.py` first to build combined files.",
                file=sys.stderr,
            )
            sys.exit(1)

    with open(recipes_path, encoding='utf-8') as f:
        recipes_data = json.load(f)

    with open(tips_path, encoding='utf-8') as f:
        tips_data = json.load(f)

    recipe_categories = sorted({entry['recipeCategory'] for entry in recipes_data['@graph']})
    tip_categories = sorted({entry['category'] for entry in tips_data})

    try:
        with open(categories_path, encoding='utf-8') as f:
            cats_data = json.load(f)
    except FileNotFoundError:
        cats_data = {}

    cats_data['recipes'] = [
        {'id': slugify(cat), 'recipeCategory': cat}
        for cat in recipe_categories
    ]
    cats_data['tips'] = [
        {'id': slugify(cat), 'category': cat}
        for cat in tip_categories
    ]

    with open(categories_path, 'w', encoding='utf-8') as f:
        json.dump(cats_data, f, indent=2, ensure_ascii=False)
        f.write('\n')

    print(f"Updated {categories_path}:")
    print(f"  {len(recipe_categories)} recipe categories:")
    for entry in cats_data['recipes']:
        print(f"    {entry['id']!r:40s} {entry['recipeCategory']}")
    print(f"  {len(tip_categories)} tip categories:")
    for entry in cats_data['tips']:
        print(f"    {entry['id']!r:40s} {entry['category']}")

if __name__ == '__main__':
    main()
