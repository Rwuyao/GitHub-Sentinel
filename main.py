import sys
import click
from cli.interactive import cli

if __name__ == "__main__":
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\n工具被手动中断")
        sys.exit(0)
    except Exception as e:
        click.echo(f"工具运行出错: {str(e)}")
        sys.exit(1)