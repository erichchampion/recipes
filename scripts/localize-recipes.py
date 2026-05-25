import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "aya-expanse:8b")
OLLAMA_OPTIONS = {"temperature": 0.3}

LOCALE_NAMES = {
    "en": "English",
    "es": "Spanish (Latin America)",
}

RECIPE_TRANSLATE_FIELDS = ["name", "keywords", "recipeIngredient", "recipeInstructions"]
TIP_TRANSLATE_FIELDS = ["title", "content"]

# Markdown tokens to strip from translated string fields
_MD_RE = re.compile(r'\*{1,3}|#{1,6} ?|`{1,3}')


def call_ollama(prompt, retries=2):
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": OLLAMA_OPTIONS,
    }).encode("utf-8")

    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                OLLAMA_URL,
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("response", "")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            if attempt < retries:
                time.sleep(2 ** attempt)
            else:
                print(f"    WARN: ollama failed after {retries + 1} attempts: {e}", file=sys.stderr)
                return None
    return None


def sanitize_json_response(text):
    """Strip markdown code fences and return cleaned text ready for json.loads."""
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```\s*$', '', text)
    return text.strip()


def clean_string_field(value):
    """Remove residual markdown tokens from a translated string."""
    if not isinstance(value, str):
        return value
    return _MD_RE.sub('', value).strip()


def clean_string_fields(obj):
    """Recursively clean markdown from all string values in a dict/list."""
    if isinstance(obj, dict):
        return {k: clean_string_fields(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_string_fields(item) for item in obj]
    if isinstance(obj, str):
        return clean_string_field(obj)
    return obj


def _is_nonempty_str(v):
    return isinstance(v, str) and v.strip() != ""


def _is_nonempty_str_list(v):
    return (
        isinstance(v, list)
        and len(v) > 0
        and all(_is_nonempty_str(item) for item in v)
    )


RECIPE_FIELD_VALIDATORS = {
    "name":               ("str",  _is_nonempty_str),
    "keywords":           ("list", _is_nonempty_str_list),
    "recipeIngredient":   ("list", _is_nonempty_str_list),
    "recipeInstructions": ("str",  _is_nonempty_str),
}

TIP_FIELD_VALIDATORS = {
    "title":   ("str", _is_nonempty_str),
    "content": ("str", _is_nonempty_str),
}


def validate_translation(source_payload, translated, validators):
    """Return True iff `translated` is a usable translation of `source_payload`.

    - `translated` must be a dict.
    - Every key present in `source_payload` must be present in `translated`
      and pass its validator predicate.
    - For list-valued fields, len(translated[k]) must equal len(source_payload[k]).
    """
    if not isinstance(translated, dict):
        return False
    for key, source_value in source_payload.items():
        if key not in validators:
            continue
        kind, predicate = validators[key]
        value = translated.get(key)
        if not predicate(value):
            return False
        if kind == "list" and len(value) != len(source_value):
            return False
    return True


def translate_recipe(entry, dest_lang, retries=3):
    payload = {k: entry[k] for k in RECIPE_TRANSLATE_FIELDS if k in entry}
    if not payload:
        return None
    prompt = (
        f'You are a professional translator. Translate the following recipe fields into {dest_lang}.\n'
        f'Return only valid JSON with the exact same structure — no markdown, no code fences, no commentary.\n'
        f'"keywords" and "recipeIngredient" must remain JSON arrays of strings.\n'
        f'"name" and "recipeInstructions" must be plain strings with no markdown formatting.\n\n'
        f'{json.dumps(payload, ensure_ascii=False)}'
    )

    for attempt in range(retries):
        raw = call_ollama(prompt, retries=2)
        if raw is None:
            return None
        try:
            translated = json.loads(sanitize_json_response(raw))
            translated = clean_string_fields(translated)
            if not validate_translation(payload, translated, RECIPE_FIELD_VALIDATORS):
                continue
            result = dict(entry)
            result.update(translated)
            return result
        except (json.JSONDecodeError, AttributeError):
            continue
    return None


def translate_tip(entry, dest_lang, retries=3):
    payload = {k: entry[k] for k in TIP_TRANSLATE_FIELDS if k in entry}
    if not payload:
        return None
    prompt = (
        f'You are a professional translator. Translate the following cooking tip fields into {dest_lang}.\n'
        f'Return only valid JSON with the exact same structure — no markdown, no code fences, no commentary.\n'
        f'"title" and "content" must be plain strings with no markdown formatting.\n\n'
        f'{json.dumps(payload, ensure_ascii=False)}'
    )

    for attempt in range(retries):
        raw = call_ollama(prompt, retries=2)
        if raw is None:
            return None
        try:
            translated = json.loads(sanitize_json_response(raw))
            translated = clean_string_fields(translated)
            if not validate_translation(payload, translated, TIP_FIELD_VALIDATORS):
                continue
            result = dict(entry)
            result.update(translated)
            return result
        except (json.JSONDecodeError, AttributeError):
            continue
    return None


def collect_missing_recipes(src_dir, dest_dir):
    """Return list of (cat_id, identifier, src_path) for recipes missing in dest."""
    missing = []
    src_recipes = src_dir / 'recipes'
    if not src_recipes.exists():
        return missing
    for src_path in sorted(src_recipes.rglob('*.json')):
        cat_id = src_path.parent.name
        identifier = src_path.stem
        dest_path = dest_dir / 'recipes' / cat_id / src_path.name
        if not dest_path.exists():
            missing.append((cat_id, identifier, src_path))
    return missing


def collect_missing_tips(src_dir, dest_dir):
    """Return list of (cat_id, tip_id, src_path) for tips missing in dest."""
    missing = []
    src_tips = src_dir / 'tips'
    if not src_tips.exists():
        return missing
    for src_path in sorted(src_tips.rglob('*.json')):
        cat_id = src_path.parent.name
        tip_id = src_path.stem
        dest_path = dest_dir / 'tips' / cat_id / src_path.name
        if not dest_path.exists():
            missing.append((cat_id, tip_id, src_path))
    return missing


def run_single_file(src_path, dest_locale):
    """Translate a single source file into dest_locale."""
    src_path = Path(src_path).resolve()
    if not src_path.is_file():
        print(f"Error: source file not found: {src_path}", file=sys.stderr)
        sys.exit(1)

    # Expect path structure: ROOT/{locale}/{recipes|tips}/{cat_id}/{filename}.json
    try:
        rel = src_path.relative_to(ROOT)
        parts = rel.parts  # e.g. ('es', 'recipes', 'sweets-desserts', 'cake.json')
        src_locale, kind, cat_id = parts[0], parts[1], parts[2]
    except (ValueError, IndexError):
        print(f"Error: cannot determine locale/kind from path: {src_path}", file=sys.stderr)
        sys.exit(1)

    if kind not in ('recipes', 'tips'):
        print(f"Error: path must contain 'recipes' or 'tips', got: {kind!r}", file=sys.stderr)
        sys.exit(1)

    dest_path = ROOT / dest_locale / kind / cat_id / src_path.name
    dest_lang = LOCALE_NAMES.get(dest_locale, dest_locale)
    tag = f"[{src_locale}→{dest_locale}]"

    if dest_path.exists():
        answer = input(f"{dest_path.relative_to(ROOT)} already exists. Overwrite? [y/N] ").strip().lower()
        if answer != 'y':
            print("Skipped.")
            return

    entry = json.loads(src_path.read_text(encoding='utf-8'))

    print(f"{tag} translating {kind}/{cat_id}/{src_path.name} …")
    if kind == 'recipes':
        result = translate_recipe(entry, dest_lang)
    else:
        result = translate_tip(entry, dest_lang)

    if result is None:
        print(f"{tag} FAIL — translation failed after retries", file=sys.stderr)
        sys.exit(1)

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f"{tag} wrote {dest_path.relative_to(ROOT)}")


def main():
    parser = argparse.ArgumentParser(
        description='Localize missing recipes and tips from one locale to another.',
        epilog='Pass a file path as SOURCE to translate a single file.',
    )
    parser.add_argument('source', help='Source locale (e.g. en) or source file path')
    parser.add_argument('dest', help='Destination locale (e.g. es)')
    args = parser.parse_args()

    # Single-file mode: source is a path to a specific JSON file
    src_as_path = Path(args.source)
    if src_as_path.suffix == '.json' or (src_as_path.exists() and src_as_path.is_file()):
        run_single_file(args.source, args.dest)
        return

    src_dir = ROOT / args.source
    dest_dir = ROOT / args.dest

    if not src_dir.is_dir():
        print(f"Error: source locale directory not found: {src_dir}", file=sys.stderr)
        sys.exit(1)
    if not dest_dir.is_dir():
        print(f"Error: dest locale directory not found: {dest_dir}", file=sys.stderr)
        sys.exit(1)

    tag = f"[{args.source}→{args.dest}]"
    dest_lang = LOCALE_NAMES.get(args.dest, args.dest)

    # --- Recipes ---
    missing_recipes = collect_missing_recipes(src_dir, dest_dir)
    total = len(missing_recipes)
    ok = skip = fail = 0

    if total == 0:
        print(f"{tag} recipes  no missing recipes")
    else:
        print(f"{tag} recipes  {total} to translate")
        for i, (cat_id, identifier, src_path) in enumerate(missing_recipes, 1):
            dest_path = dest_dir / 'recipes' / cat_id / src_path.name
            label = f"{cat_id}/{src_path.name}"

            if dest_path.exists():
                skip += 1
                continue

            try:
                entry = json.loads(src_path.read_text(encoding='utf-8'))
            except (OSError, json.JSONDecodeError) as e:
                fail += 1
                print(f"{tag} recipes  {i}/{total}  FAIL  {label}  (source read/parse: {e})  (ok={ok}, skip={skip}, fail={fail})")
                continue

            result = translate_recipe(entry, dest_lang)

            if result is None:
                fail += 1
                print(f"{tag} recipes  {i}/{total}  FAIL  {label}  (ok={ok}, skip={skip}, fail={fail})")
            else:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                dest_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
                ok += 1
                print(f"{tag} recipes  {i}/{total}  {label}  (ok={ok}, skip={skip}, fail={fail})")

    print(f"{tag} recipes  done — ok={ok}, skip={skip}, fail={fail}")

    # --- Tips ---
    missing_tips = collect_missing_tips(src_dir, dest_dir)
    total = len(missing_tips)
    ok = skip = fail = 0

    if total == 0:
        print(f"{tag} tips     no missing tips")
    else:
        print(f"{tag} tips     {total} to translate")
        for i, (cat_id, tip_id, src_path) in enumerate(missing_tips, 1):
            dest_path = dest_dir / 'tips' / cat_id / src_path.name
            label = f"{cat_id}/{src_path.name}"

            if dest_path.exists():
                skip += 1
                continue

            try:
                entry = json.loads(src_path.read_text(encoding='utf-8'))
            except (OSError, json.JSONDecodeError) as e:
                fail += 1
                print(f"{tag} tips     {i}/{total}  FAIL  {label}  (source read/parse: {e})  (ok={ok}, skip={skip}, fail={fail})")
                continue

            result = translate_tip(entry, dest_lang)

            if result is None:
                fail += 1
                print(f"{tag} tips     {i}/{total}  FAIL  {label}  (ok={ok}, skip={skip}, fail={fail})")
            else:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                dest_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
                ok += 1
                print(f"{tag} tips     {i}/{total}  {label}  (ok={ok}, skip={skip}, fail={fail})")

    print(f"{tag} tips     done — ok={ok}, skip={skip}, fail={fail}")


if __name__ == '__main__':
    main()
