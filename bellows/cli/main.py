import logging

import click
import click_log

from . import opts


@click.group()
@click_log.simple_verbosity_option(logging.getLogger(), default="INFO")
@opts.device
@opts.baudrate
@opts.flow_control
@click.pass_context
def main(ctx, device, baudrate, flow_control):
    ctx.obj = {
        "device": device,
        "baudrate": baudrate,
        "flow_control": flow_control,
    }
    click_log.basic_config()


if __name__ == "__main__":
    main()
