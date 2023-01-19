import python_coreml_stable_diffusion.pipeline as pipeline
from python_coreml_stable_diffusion.pipeline import logger

from interface import UI


def main():
    args = pipeline.parse_args()

    if not args.mock:
        logger.info("Using CoreML model")
        model = pipeline.load_model(args)
    else:
        logger.info("Using mock model")
        model = pipeline.ModelMock()

    ui = UI(model, logger, args)
    ui.exec()


if __name__ == '__main__':
    main()
