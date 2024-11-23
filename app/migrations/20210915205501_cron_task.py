# Generated by database migrator
import peewee


def migrate(migrator, database, **kwargs):
    migrator.add_columns("schedules", cron_string=peewee.CharField(default=""))
    """
    Write your migrations here.
    """


def rollback(migrator, database, **kwargs):
    migrator.drop_columns("schedules", ["cron_string"])
    """
    Write your rollback migrations here.
    """
