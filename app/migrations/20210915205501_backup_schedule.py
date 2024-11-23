# Generated by database migrator
import peewee
from app.classes.models.management import Schedules


def migrate(migrator, database, **kwargs):
    migrator.drop_columns("backups", ["schedule_id"])
    """
    Write your migrations here.
    """


def rollback(migrator, database, **kwargs):
    migrator.add_columns(
        "backups",
        schedule_id=peewee.ForeignKeyField(Schedules, backref="backups_schedule"),
    )
    """
    Write your rollback migrations here.
    """