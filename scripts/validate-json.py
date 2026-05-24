import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

PASS = "✓"
FAIL = "✗"


def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def load_category_map(categories_path):
    data = json.loads(categories_path.read_text(encoding='utf-8'))
    recipe_map = {entry['recipeCategory']: entry['id'] for entry in data['recipes']}
    tip_map = {entry['category']: entry['id'] for entry in data['tips']}
    return recipe_map, tip_map


def find_locales(root):
    return [
        d for d in sorted(root.iterdir())
        if d.is_dir() and (d / 'recipes.json').exists() and (d / 'tips.json').exists()
    ]


def report(ok, message):
    print(f"  {'  ' if ok else ''}{PASS if ok else FAIL} {message}")
    return ok


def validate_recipes(locale_dir, recipe_map):
    errors = 0
    source = locale_dir / 'recipes.json'
    combined = json.loads(source.read_text(encoding='utf-8'))['@graph']

    # Check for duplicate identifiers in combined file
    ids_seen = {}
    for entry in combined:
        ident = entry.get('identifier')
        ids_seen[ident] = ids_seen.get(ident, 0) + 1
    dupes = {k: v for k, v in ids_seen.items() if v > 1}
    if dupes:
        for ident, count in sorted(dupes.items()):
            report(False, f"duplicate identifier in combined: {ident!r} ({count}x)")
            errors += 1
    else:
        report(True, f"no duplicate identifiers in combined ({len(combined)} entries)")

    # Index combined by identifier
    combined_by_id = {entry['identifier']: entry for entry in combined}

    # Collect individual files
    split_files = list((locale_dir / 'recipes').rglob('*.json'))
    split_by_id = {}
    dupe_files = []
    for path in split_files:
        entry = json.loads(path.read_text(encoding='utf-8'))
        ident = entry.get('identifier')
        if ident in split_by_id:
            dupe_files.append(ident)
        split_by_id[ident] = (path, entry)

    if dupe_files:
        for ident in sorted(dupe_files):
            report(False, f"duplicate identifier in split files: {ident!r}")
            errors += 1
    else:
        report(True, f"no duplicate identifiers in split files ({len(split_files)} files)")

    # Count match
    if len(combined) == len(split_files):
        report(True, f"counts match: {len(combined)}")
    else:
        report(False, f"count mismatch: combined={len(combined)}, split files={len(split_files)}")
        errors += 1

    # Entries in combined but missing as split files
    missing_splits = sorted(set(combined_by_id) - set(split_by_id))
    if missing_splits:
        report(False, f"{len(missing_splits)} combined entries have no split file")
        for ident in missing_splits[:10]:
            print(f"      missing: {ident}")
        if len(missing_splits) > 10:
            print(f"      ... and {len(missing_splits) - 10} more")
        errors += 1
    else:
        report(True, "every combined entry has a split file")

    # Split files with no combined entry
    orphans = sorted(set(split_by_id) - set(combined_by_id))
    if orphans:
        report(False, f"{len(orphans)} split files have no combined entry")
        for ident in orphans[:10]:
            print(f"      orphan: {ident}")
        if len(orphans) > 10:
            print(f"      ... and {len(orphans) - 10} more")
        errors += 1
    else:
        report(True, "every split file has a combined entry")

    # Content equality and correct category directory
    content_diffs = []
    wrong_dir = []
    for ident, (path, split_entry) in split_by_id.items():
        combined_entry = combined_by_id.get(ident)
        if combined_entry is None:
            continue
        if split_entry != combined_entry:
            content_diffs.append(ident)
        # Check category directory
        cat = combined_entry.get('recipeCategory', '')
        expected_cat_id = recipe_map.get(cat, slugify(cat))
        expected_dir = locale_dir / 'recipes' / expected_cat_id
        if path.parent != expected_dir:
            wrong_dir.append((ident, path.parent.name, expected_cat_id))

    if content_diffs:
        report(False, f"{len(content_diffs)} split files differ from combined entry")
        for ident in content_diffs[:10]:
            print(f"      diff: {ident}")
        if len(content_diffs) > 10:
            print(f"      ... and {len(content_diffs) - 10} more")
        errors += 1
    else:
        report(True, "all split file contents match combined entries")

    if wrong_dir:
        report(False, f"{len(wrong_dir)} recipes in wrong category directory")
        for ident, actual, expected in wrong_dir[:10]:
            print(f"      {ident}: in {actual!r}, expected {expected!r}")
        if len(wrong_dir) > 10:
            print(f"      ... and {len(wrong_dir) - 10} more")
        errors += 1
    else:
        report(True, "all recipes are in the correct category directory")

    return errors


def validate_tips(locale_dir, tip_map):
    errors = 0
    source = locale_dir / 'tips.json'
    combined = json.loads(source.read_text(encoding='utf-8'))

    # Check for duplicate ids in combined file
    ids_seen = {}
    for entry in combined:
        tip_id = entry.get('id')
        ids_seen[tip_id] = ids_seen.get(tip_id, 0) + 1
    dupes = {k: v for k, v in ids_seen.items() if v > 1}
    if dupes:
        for tip_id, count in sorted(dupes.items()):
            report(False, f"duplicate id in combined: {tip_id!r} ({count}x)")
            errors += 1
    else:
        report(True, f"no duplicate ids in combined ({len(combined)} entries)")

    combined_by_id = {entry['id']: entry for entry in combined}

    split_files = list((locale_dir / 'tips').rglob('*.json'))
    split_by_id = {}
    dupe_files = []
    for path in split_files:
        entry = json.loads(path.read_text(encoding='utf-8'))
        tip_id = entry.get('id')
        if tip_id in split_by_id:
            dupe_files.append(tip_id)
        split_by_id[tip_id] = (path, entry)

    if dupe_files:
        for tip_id in sorted(dupe_files):
            report(False, f"duplicate id in split files: {tip_id!r}")
            errors += 1
    else:
        report(True, f"no duplicate ids in split files ({len(split_files)} files)")

    if len(combined) == len(split_files):
        report(True, f"counts match: {len(combined)}")
    else:
        report(False, f"count mismatch: combined={len(combined)}, split files={len(split_files)}")
        errors += 1

    missing_splits = sorted(set(combined_by_id) - set(split_by_id))
    if missing_splits:
        report(False, f"{len(missing_splits)} combined entries have no split file")
        for tip_id in missing_splits:
            print(f"      missing: {tip_id}")
        errors += 1
    else:
        report(True, "every combined entry has a split file")

    orphans = sorted(set(split_by_id) - set(combined_by_id))
    if orphans:
        report(False, f"{len(orphans)} split files have no combined entry")
        for tip_id in orphans:
            print(f"      orphan: {tip_id}")
        errors += 1
    else:
        report(True, "every split file has a combined entry")

    content_diffs = []
    wrong_dir = []
    for tip_id, (path, split_entry) in split_by_id.items():
        combined_entry = combined_by_id.get(tip_id)
        if combined_entry is None:
            continue
        if split_entry != combined_entry:
            content_diffs.append(tip_id)
        cat = combined_entry.get('category', '')
        expected_cat_id = tip_map.get(cat, slugify(cat))
        expected_dir = locale_dir / 'tips' / expected_cat_id
        if path.parent != expected_dir:
            wrong_dir.append((tip_id, path.parent.name, expected_cat_id))

    if content_diffs:
        report(False, f"{len(content_diffs)} split files differ from combined entry")
        for tip_id in content_diffs:
            print(f"      diff: {tip_id}")
        errors += 1
    else:
        report(True, "all split file contents match combined entries")

    if wrong_dir:
        report(False, f"{len(wrong_dir)} tips in wrong category directory")
        for tip_id, actual, expected in wrong_dir:
            print(f"      {tip_id}: in {actual!r}, expected {expected!r}")
        errors += 1
    else:
        report(True, "all tips are in the correct category directory")

    return errors


def main():
    recipe_map, tip_map = load_category_map(ROOT / 'categories.json')
    locales = find_locales(ROOT)
    total_errors = 0

    for locale_dir in locales:
        locale = locale_dir.name

        print(f"\n[{locale}] recipes")
        total_errors += validate_recipes(locale_dir, recipe_map)

        print(f"\n[{locale}] tips")
        total_errors += validate_tips(locale_dir, tip_map)

    print()
    if total_errors == 0:
        print(f"{PASS} All checks passed.")
    else:
        print(f"{FAIL} {total_errors} check(s) failed.")
        sys.exit(1)


if __name__ == '__main__':
    main()
