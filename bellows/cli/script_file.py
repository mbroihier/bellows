import asyncio
async def entry(ctx, commandList, click):
    v = await commandList['b0:c7:de:ff:fe:52:ca:58on']()
    click.echo(v)
    await asyncio.sleep(5.0)
    v = await commandList['b0:c7:de:ff:fe:52:ca:58off']()
    click.echo(v)
