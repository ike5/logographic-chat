import click
from .auth import load_credentials, device_login, clear_credentials, refresh_access_token

DEFAULT_SERVER = "https://chat.codebylevel.com"


@click.group(invoke_without_command=True)
@click.option("--server", default=DEFAULT_SERVER, envvar="LOGOGRAPHIC_SERVER")
@click.pass_context
def main(ctx, server):
    """Logographic Chat — a TUI chat client."""
    ctx.ensure_object(dict)
    ctx.obj["server"] = server
    if ctx.invoked_subcommand is not None:
        return

    creds = load_credentials()
    if not creds:
        click.echo("Welcome to Logographic Chat!")
        click.echo("You need to sign in first.\n")
        creds = device_login(server)
    else:
        refreshed = refresh_access_token(server)
        if refreshed:
            creds = refreshed
        else:
            click.echo("Session expired. Please sign in again.\n")
            creds = device_login(server)

    from .tui import ChatApp
    app = ChatApp(server_url=server, access_token=creds["access_token"], username=creds["username"])
    app.run()


@main.command()
@click.pass_context
def login(ctx):
    """Authenticate with the server."""
    device_login(ctx.obj["server"])


@main.command()
def logout():
    """Remove stored credentials."""
    clear_credentials()
    click.echo("Logged out.")
