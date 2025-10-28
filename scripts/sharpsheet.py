# Sharpsheet is a asynchonous spritesheet generator.
import asyncio
import logging
import os

from click import command


class Sharpsheet:
    def __init__(self, *args, **kwargs):
        self.logger = kwargs.get('logger', logging.getLogger('Sharpsheet'))

    async def generateFromPath(self, inputPath, *args, **kwargs):
        self.logger.debug("generate spritesheet from {}".format(inputPath))
        format = kwargs.get('format', 'jpg')
        quality = kwargs.get('quality', 60)
        dimension = kwargs.get('dimension', '2048')
        spriteSize = kwargs.get('spriteSize', '128')
        outputPath = kwargs.get('outputPath', os.path.abspath(
            os.path.join(inputPath, '../sprites/')))
        input = inputPath + '/*.jpg'

        command = [
            # 'sharpsheet',
            '/modules/sharpsheet/bin/sharpsheet.js',
            input,
            '--outputPath', outputPath,
            '--outputFormat', format,
            '--outputQuality', quality.__str__(),
            '--sheetDimension', dimension.__str__(),
            '--spriteSize', spriteSize.__str__()
        ]
        print(command.__str__())

        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)

        stdout, stderr = await proc.communicate()

        self.logger.info("stdout: {}".format(stdout.decode()))

        if stderr:
            self.logger.error(
                "error generating spritesheet: {}".format(stderr.decode()))
            return False
        else:
            self.logger.info("spritesheet generated")
            return outputPath


if __name__ == '__main__':
    spriter = Sharpsheet()
    asyncio.run(
        spriter.generate('/data/Broadsides/images/thumbs/')
    )
