import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
RECIPE_REQUIRED = {"@type", "identifier", "name", "recipeCuisine", "recipeCategory"}
TIP_REQUIRED = {"id", "title", "category"}


def load_reverse_maps(categories_path):
    data = json.loads(categories_path.read_text(encoding='utf-8'))
    recipe_id_to_cat = {entry['id']: entry['recipeCategory'] for entry in data['recipes']}
    tip_id_to_cat = {entry['id']: entry['category'] for entry in data['tips']}
    return recipe_id_to_cat, tip_id_to_cat


def find_locales(root):
    return [
        d for d in sorted(root.iterdir())
        if d.is_dir() and (d / 'recipes').is_dir() and (d / 'tips').is_dir()
    ]


def collect_recipes(locale_dir, recipe_id_to_cat):
    errors = []
    seen_ids = {}
    entries = []

    for path in sorted((locale_dir / 'recipes').rglob('*.json')):
        cat_id = path.parent.name
        try:
            entry = json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as e:
            errors.append(f"{path.relative_to(ROOT)}: invalid JSON: {e}")
            continue

        missing = RECIPE_REQUIRED - entry.keys()
        if missing:
            errors.append(f"{path.relative_to(ROOT)}: missing fields: {sorted(missing)}")
            continue

        if entry['@type'] != 'Recipe':
            errors.append(f"{path.relative_to(ROOT)}: @type must be 'Recipe', got {entry['@type']!r}")

        expected_id = path.stem
        if entry['identifier'] != expected_id:
            errors.append(
                f"{path.relative_to(ROOT)}: identifier {entry['identifier']!r} does not match filename {expected_id!r}"
            )

        if cat_id not in recipe_id_to_cat:
            errors.append(f"{path.relative_to(ROOT)}: unknown category directory {cat_id!r}")
        else:
            entry['recipeCategory'] = recipe_id_to_cat[cat_id]

        ident = entry['identifier']
        if ident in seen_ids:
            errors.append(f"{path.relative_to(ROOT)}: duplicate identifier {ident!r} (also in {seen_ids[ident]})")
        else:
            seen_ids[ident] = str(path.relative_to(ROOT))

        entries.append(entry)

    return entries, errors


def collect_tips(locale_dir, tip_id_to_cat):
    errors = []
    seen_ids = {}
    entries = []

    for path in sorted((locale_dir / 'tips').rglob('*.json')):
        cat_id = path.parent.name
        try:
            entry = json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as e:
            errors.append(f"{path.relative_to(ROOT)}: invalid JSON: {e}")
            continue

        missing = TIP_REQUIRED - entry.keys()
        if missing:
            errors.append(f"{path.relative_to(ROOT)}: missing fields: {sorted(missing)}")
            continue

        expected_id = path.stem
        if entry['id'] != expected_id:
            errors.append(
                f"{path.relative_to(ROOT)}: id {entry['id']!r} does not match filename {expected_id!r}"
            )

        if cat_id not in tip_id_to_cat:
            errors.append(f"{path.relative_to(ROOT)}: unknown category directory {cat_id!r}")
        else:
            entry['category'] = tip_id_to_cat[cat_id]

        tip_id = entry['id']
        if tip_id in seen_ids:
            errors.append(f"{path.relative_to(ROOT)}: duplicate id {tip_id!r} (also in {seen_ids[tip_id]})")
        else:
            seen_ids[tip_id] = str(path.relative_to(ROOT))

        entries.append(entry)

    return entries, errors


def read_context(recipes_json_path):
    if recipes_json_path.exists():
        try:
            data = json.loads(recipes_json_path.read_text(encoding='utf-8'))
            return data.get('@context', 'https://schema.org')
        except json.JSONDecodeError:
            pass
    return 'https://schema.org'


def main():
    recipe_id_to_cat, tip_id_to_cat = load_reverse_maps(ROOT / 'categories.json')
    locales = find_locales(ROOT)

    all_errors = []
    pending = []

    for locale_dir in locales:
        locale = locale_dir.name

        recipes, recipe_errors = collect_recipes(locale_dir, recipe_id_to_cat)
        tips, tip_errors = collect_tips(locale_dir, tip_id_to_cat)

        all_errors.extend(recipe_errors)
        all_errors.extend(tip_errors)

        context = read_context(locale_dir / 'recipes.json')
        pending.append((locale_dir, locale, recipes, tips, context))

    if all_errors:
        print(f"Validation failed — {len(all_errors)} error(s), nothing written:\n")
        for err in all_errors:
            print(f"  ✗ {err}")
        sys.exit(1)

    for locale_dir, locale, recipes, tips, context in pending:
        recipes.sort(key=lambda r: r['identifier'])
        tips.sort(key=lambda t: t['id'])

        recipes_out = locale_dir / 'recipes.json'
        recipes_out.write_text(
            json.dumps({'@context': context, '@graph': recipes}, indent=2, ensure_ascii=False) + '\n',
            encoding='utf-8',
        )

        tips_out = locale_dir / 'tips.json'
        tips_out.write_text(
            json.dumps(tips, indent=2, ensure_ascii=False) + '\n',
            encoding='utf-8',
        )

        print(f"{locale}: wrote {len(recipes)} recipes, {len(tips)} tips")


if __name__ == '__main__':
    main()
