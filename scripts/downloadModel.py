import asyncio
from featureExtractor import FeatureExtractor


async def main():
    print("Starting featureExtractor")
    extractor = FeatureExtractor()
    print("Loading model")
    extractor.load_model(local=False)
    print("Saving model")
    extractor.save_model()


if __name__ == "__main__":
    asyncio.run(main())
