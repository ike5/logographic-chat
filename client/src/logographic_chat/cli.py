import click

DEFAULT_SERVER = "https://chat.codebylevel.com"


def handle_main_tui(server):
    """Handle the actual TUI functionality in a separate function."""
    from logographic_chat.auth import load_credentials, device_login, refresh_access_token, debug, error

    debug("CLI starting", server=server)
    creds = load_credentials()
    if not creds:
        click.echo("Welcome to Logographic Chat!")
        click.echo("You need to sign in first.\n")
        creds = device_login(server)
    else:
        debug("Found stored credentials, attempting refresh")
        refreshed = refresh_access_token(server)
        if refreshed:
            creds = refreshed
        else:
            click.echo("Session expired. Please sign in again.\n")
            creds = device_login(server)

    debug("Launching TUI", server=server, username=creds["username"])
    try:
        from logographic_chat.tui import ChatApp
        app = ChatApp(server_url=server, access_token=creds["access_token"], username=creds["username"])
        app.run()
    except Exception as e:
        error("TUI crashed", error=str(e))
        raise


@click.group(invoke_without_command=True)
@click.option("--server", default=DEFAULT_SERVER, envvar="LOGOGRAPHIC_SERVER")
@click.pass_context
def main(ctx, server):
    """Logographic Chat — a TUI chat client."""
    ctx.ensure_object(dict)
    ctx.obj["server"] = server
    if ctx.invoked_subcommand is not None:
        return

    # Only load async dependencies when actually running the TUI
    handle_main_tui(server)


@main.command()
@click.option("--server", default=DEFAULT_SERVER, envvar="LOGOGRAPHIC_SERVER")
@click.pass_context
def login(ctx, server):
    """Authenticate with the server."""
    from logographic_chat.auth import device_login
    device_login(server)


@main.command()
def logout():
    """Remove stored credentials."""
    from logographic_chat.auth import clear_credentials
    clear_credentials()
    click.echo("Logged out.")


if __name__ == "__main__":
    main()
