# Sharpsheet is a asynchonous spritesheet generator.
import asyncio
import logging
import os
import httpx

from click import command


class Sharpsheet:
    def __init__(self, *args, **kwargs):
        self.logger = kwargs.get('logger', logging.getLogger('Sharpsheet'))
        self.api_url = kwargs.get('api_url', 'http://sharpsheet:3000')

    async def generateFromPath(self, inputPath, *args, **kwargs):
        self.logger.debug("generate spritesheet from {}".format(inputPath))
        format = kwargs.get('format', 'jpg')
        quality = kwargs.get('quality', 60)
        dimension = kwargs.get('dimension', '2048')
        spriteSize = kwargs.get('spriteSize', '128')
        outputPath = kwargs.get('outputPath', os.path.abspath(
            os.path.join(inputPath, '../sprites/')))

        payload = {
            'inputPath': inputPath,
            'outputPath': outputPath,
            'format': format,
            'quality': quality,
            'dimension': dimension,
            'spriteSize': spriteSize
        }

        self.logger.info(f"Sending request to sharpsheet API: {payload}")

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.api_url}/generate",
                    json=payload
                )
                response.raise_for_status()
                result = response.json()

                if result.get('success'):
                    self.logger.info("spritesheet generated")
                    if result.get('stdout'):
                        self.logger.info(f"stdout: {result['stdout']}")
                    return outputPath
                else:
                    error_msg = result.get('error', 'Unknown error')
                    if result.get('stderr'):
                        self.logger.error(f"stderr: {result['stderr']}")
                    self.logger.error(f"error generating spritesheet: {error_msg}")
                    return False

        except httpx.HTTPError as e:
            self.logger.error(f"HTTP error generating spritesheet: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error generating spritesheet: {e}")
            return False


if __name__ == '__main__':
    spriter = Sharpsheet()
    asyncio.run(
        spriter.generate('/data/Broadsides/images/thumbs/')
    )
