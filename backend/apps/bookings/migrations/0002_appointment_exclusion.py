from django.db import migrations


CONSTRAINT_NAME = "exclude_overlapping_active_appointments"
TABLE_NAME = "bookings_appointment"


def create_exclusion_constraint(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    schema_editor.execute(
        f"""
        ALTER TABLE {TABLE_NAME}
        ADD CONSTRAINT {CONSTRAINT_NAME}
        EXCLUDE USING gist (
            staff_id WITH =,
            tstzrange(starts_at, ends_at, '[)') WITH &&
        )
        WHERE (status IN ('pending', 'confirmed'))
        """
    )


def drop_exclusion_constraint(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(f"ALTER TABLE {TABLE_NAME} DROP CONSTRAINT IF EXISTS {CONSTRAINT_NAME}")


class Migration(migrations.Migration):
    dependencies = [
        ("bookings", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_exclusion_constraint, drop_exclusion_constraint),
    ]
