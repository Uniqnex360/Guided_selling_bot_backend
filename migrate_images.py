"""
One-time migration: convert product.images from a list of plain URL strings
into a list of {"name": "", "url": <string>} objects.

Safe to re-run: any element that's already a dict is left untouched, so
running this twice (or on a partially-migrated collection) is harmless.

Usage:
    python migrate_images.py            # dry run, prints what WOULD change
    python migrate_images.py --apply    # actually writes changes

Run this from the same environment/venv that has mongoengine configured
(i.e. wherever guidedProductAssistant.models can be imported), or adjust
the import + connect() call below to match your project's DB settings.
"""
import sys
from guidedProductAssistant.models import product  # adjust import path if needed


def migrate(apply_changes: bool):
    total = 0
    changed = 0
    skipped_already_ok = 0
    errors = 0

    for prod in product.objects():
        total += 1
        images = prod.images or []

        if not images:
            continue

        needs_update = False
        new_images = []

        for entry in images:
            if isinstance(entry, dict):
                # Already migrated (or created fresh by new import code) - leave as is.
                new_images.append(entry)
            elif isinstance(entry, str):
                if entry.strip():
                    new_images.append({"name": "", "url": entry.strip()})
                    needs_update = True
                else:
                    # drop empty strings entirely
                    needs_update = True
            else:
                # Unexpected type - keep a record but don't crash the migration.
                print(f"  [WARN] product {prod.id}: unexpected image entry type "
                      f"{type(entry)} -> {entry!r}, skipping this entry")
                errors += 1

        if not needs_update:
            skipped_already_ok += 1
            continue

        changed += 1
        print(f"product {prod.id} ({prod.product_name!r}): "
              f"{len(images)} old entries -> {len(new_images)} new entries")

        if apply_changes:
            prod.images = new_images
            prod.save()

    print("\n--- Migration summary ---")
    print(f"Total products scanned : {total}")
    print(f"Already in new format  : {skipped_already_ok}")
    print(f"Converted{' (applied)' if apply_changes else ' (dry run, not saved)'}"
          f"           : {changed}")
    if errors:
        print(f"Entries with unexpected type (left as-is): {errors}")

    if not apply_changes and changed > 0:
        print("\nThis was a DRY RUN. Re-run with --apply to write these changes.")


if __name__ == "__main__":
    apply_changes = "--apply" in sys.argv
    migrate(apply_changes)