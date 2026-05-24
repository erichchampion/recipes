# Recipes

A structured recipe and cooking-tips archive in English and Spanish, organized by category.

## Content

The archive contains:

- **73,710** English recipes across 11 categories
- **56,739** Spanish recipes across 11 categories
- **55** cooking tips per locale across 10 categories

Recipes and tips are stored as individual JSON files, one per recipe or tip, organized by locale and category. The combined per-locale `recipes.json` and `tips.json` files are derived from these and are not tracked in git.

### Repository layout

```
categories.json          # canonical category list for recipes and tips
en/
  recipes/
    baked-goods/
      some-recipe.json
    sweets-desserts/
      another-recipe.json
    ...                  # 11 category directories
  tips/
    cooking-methods/
      tip-id.json
    ...                  # 10 category directories
es/
  recipes/...
  tips/...
scripts/
  create-categories.py
  split-json.py
  combine-json.py
  validate-json.py
  localize-recipes.py
```

### Recipe file structure

```json
{
  "@type": "Recipe",
  "identifier": "recipe-slug",
  "name": "Recipe Title",
  "recipeCuisine": "Non-regional",
  "recipeCategory": "Sweets & Desserts",
  "keywords": ["tag1", "tag2"],
  "recipeIngredient": ["1 cup flour", "..."],
  "recipeInstructions": "Step-by-step instructions…",
  "url": null
}
```

### Tip file structure

```json
{
  "id": "tip-slug",
  "title": "Tip Title",
  "category": "Cooking Methods",
  "content": "Tip content…"
}
```

## Setup

```sh
python3 -m venv .venv
source .venv/bin/activate
```

No third-party packages are required. All scripts use the standard library only, except `localize-recipes.py` which requires a running [Ollama](https://ollama.com) instance.

## Scripts

All scripts are run from the project root.

### `scripts/create-categories.py`

Rebuilds `categories.json` by scanning the unique `recipeCategory` values in `en/recipes.json` and the unique `category` values in `en/tips.json`. Run this if new categories are introduced.

```sh
python scripts/create-categories.py
```

### `scripts/split-json.py`

Splits the combined `{locale}/recipes.json` and `{locale}/tips.json` files into individual per-recipe and per-tip JSON files, organized by category slug.

```sh
python scripts/split-json.py
```

Output: `{locale}/recipes/{category-slug}/{identifier}.json` and `{locale}/tips/{category-slug}/{id}.json`

### `scripts/combine-json.py`

The inverse of `split-json.py`. Reconstructs the combined `{locale}/recipes.json` and `{locale}/tips.json` from the individual split files. Validates required fields and unique IDs before writing; aborts on any error. The `recipeCategory` and `category` values are sourced from `categories.json` via the parent directory name, overriding whatever is stored in each file.

```sh
python scripts/combine-json.py
```

### `scripts/validate-json.py`

Validates that the individual split files and the combined locale files are consistent. Checks for duplicate IDs, count mismatches, content differences, and files placed in the wrong category directory.

```sh
python scripts/validate-json.py
```

### `scripts/localize-recipes.py`

Translates recipes and tips that are present in a source locale but missing from a destination locale, using [Ollama](https://ollama.com) (`aya-expanse:8b` by default). Skips files that already exist in the destination. The `identifier`, `id`, `recipeCategory`, and `category` fields are never translated.

**Batch mode** — translate all missing files between two locales:

```sh
python scripts/localize-recipes.py en es
python scripts/localize-recipes.py es en
```

**Single-file mode** — translate one specific file:

```sh
python scripts/localize-recipes.py en/recipes/sweets-desserts/grapefruit-cake.json es
```

Prompts before overwriting an existing destination file.

Override the model with the `OLLAMA_MODEL` environment variable:

```sh
OLLAMA_MODEL=llama3.1:8b python scripts/localize-recipes.py en es
```

---

## Provenance

*A library built by hand, one post at a time.*

In 1993, while a student at Berkeley, Jennifer Snider discovered Usenet newsgroups and the curious habit certain strangers had of posting their grandmothers' recipes there. She began saving them. Two years later, the collection went up on the web as SOAR — the Searchable Online Archive of Recipes, and later became RecipeSource. Rosemary & Thyme is, in a sense, the archive's third life: each recipe gently rewritten by a small language model, scored for quality, sorted by region and type, and bound up again for a phone-sized shelf.

With profound thanks to Jennifer Snider, and to every cook who ever pressed "send."

**Visit the original archive**

RecipeSource on archive.org:
https://web.archive.org/web/20200108184829/https://www.recipesource.com/

*The certificate has long since expired — but the recipes endure.*

---

## Origen

*Una biblioteca construida a mano, una publicación a la vez.**

En 1993, mientras estudiaba en Berkeley, Jennifer Snider descubrió
los grupos de noticias de Usenet y la curiosa costumbre que tenían ciertos
extraños de publicar las recetas de sus abuelas. Empezó a guardarlas. Dos
años después, la colección apareció en la web como SOAR — el
Archivo de Recetas en Línea, Buscable, y más tarde se convirtió en
RecipeSource. Rosemary & Thyme es, en cierto sentido, la
tercera vida del archivo: cada receta reescrita con cuidado por un
pequeño modelo de lenguaje, calificada por calidad, ordenada por región
y tipo, y encuadernada de nuevo para un estante del tamaño de un teléfono.

Con profundo agradecimiento a Jennifer Snider, y a cada cocinero
que alguna vez pulsó “enviar.”

**Visita el archivo original**

RecipeSource en archive.org:
https://web.archive.org/web/20200108184829/https://www.recipesource.com/

*El certificado caducó hace tiempo — pero las recetas perduran.*

