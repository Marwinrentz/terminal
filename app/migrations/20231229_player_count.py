# Generated by database migrator
import peewee


def migrate(migrator, database, **kwargs):
    migrator.add_columns("servers", count_players=peewee.BooleanField(default=True))
    """
    Write your migrations here.
    """


def rollback(migrator, database, **kwargs):
    migrator.drop_columns("servers", ["count_players"])
    """
    Write your rollback migrations here.
    """