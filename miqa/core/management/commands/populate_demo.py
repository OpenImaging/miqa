import djclick as click

from miqa.core.management.populate_demo import populate_demo


@click.command()
def command():
    populate_demo()

    print('Demo Project reset.')
