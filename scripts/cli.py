import asyncio
from main import create_instance, crawl_collection, crawl_images, make_spritesheets, make_features, make_umap, make_metadata, make_zip, DEFAULTS
# import fire
import sys

# example:
# python cli.py https://resource.swissartresearch.net/manifest/zbz-collection-100 collection.worker=3 collection.depth=1

async def main():
    print("Starting...")

    if len(sys.argv) < 2:
        print("Please provide a url")
        sys.exit(1)

    url = sys.argv[1]
    if not url.startswith("http"):
        print("Please provide a url")
        sys.exit(1)
        
    for arg in sys.argv[2:]:
        print(arg)
        key, value = arg.split("=")
        key1, key2 = key.split(".")
        DEFAULTS[key1][key2] = value
    
    print("DEFAULTS: {}".format(DEFAULTS))
 
    config = await create_instance(url)
    instance_id = config['id']

    await crawl_collection(instance_id, worker=DEFAULTS["collection"]["worker"], depth=DEFAULTS["collection"]["depth"], skip_cache=DEFAULTS["collection"]["skip_cache"])
    await crawl_images(instance_id, worker=DEFAULTS["images"]["worker"], skip_cache=DEFAULTS["images"]["skip_cache"])
    await make_spritesheets(instance_id)
    await make_features(instance_id, batch_size=DEFAULTS["features"]["batch_size"], skip_cache=DEFAULTS["features"]["skip_cache"])
    await make_umap(instance_id, n_neighbors=DEFAULTS["umap"]["n_neighbors"], min_distance=DEFAULTS["umap"]["min_distance"], raster_fairy=DEFAULTS["umap"]["raster_fairy"])
    await make_metadata(instance_id, skip_cache=DEFAULTS["metadata"]["skip_cache"])
    await make_zip(instance_id)

    print("Done")
    print(config)


if __name__ == "__main__":
    asyncio.run(main())
    # asyncio.run(fire.Fire(main))