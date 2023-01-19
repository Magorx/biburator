from PyQt6.QtGui import QColor, QImage

import PIL

import numpy as np
import os


def ndarray_to_image(image):
    # convert numpy array to QPixmap
    qt_image = QImage(image.shape[1], image.shape[0], QImage.Format.Format_RGB888)
    for x in range(image.shape[1]):
        for y in range(image.shape[0]):
            qt_image.setPixel(x, y, QColor(image[y, x, 0], image[y, x, 1], image[y, x, 2]).rgb())
    
    return qt_image


class ImageGenerator:
    def __init__(self, model, logger, args={}):
        self.model = model
        self.logger = logger
        self.args = args

        self.is_generating = False
        self.is_cancelled = False

        self.reset_history()

        self.history_frame_duration = 100
        self.history_looped = True

    def reset_history(self):
        self.image = None
        self.history = {
            "prompt": None,
            "steps": None,
            "guidence": None,
            "seed": None,
            "images" : []
        }
    
    def start_generation(self):
        self.reset_history()
        self.is_generating = True
    
    def cancel_generation(self):
        self.is_cancelled = True
    
    def end_generation(self, to_save_image=True, to_save_history=True):
        self.is_generating = False
        self.is_cancelled = False

        if to_save_image:
            self.save_image()
        
        if to_save_history:
            self.save_history()

    def save_image(self):
        path = self.generate_image_path() + '.png'
        image = PIL.Image.fromarray(self.image)
        print(str(path))
        image.save(path)

    def save_history(self):
        path = self.generate_image_path() + ".gif"
        images = [PIL.Image.fromarray(img) for img in self.history["images"]]
        images[0].save(path, save_all=True, append_images=images[1:], duration=self.history_frame_duration)

    def generate_image_path(self):
        prompt = self.history["prompt"]
        folder = os.path.join(self.args.o, "_".join(prompt.replace("/", "_").rsplit(" ")))
        os.makedirs(folder, exist_ok=True)

        name = f"{self.history['seed']}_{len(self.history['images'])}_{self.history['guidence']}"
        return os.path.join(folder, name)

    def create_step_callback(self, external_callback):
        def callback(iter, time_left, latents):
            if latents is None:
                image = (np.random.random((512, 512, 3)) * 255).astype(np.uint8)
            else:
                image = (self.model.decode_latents(latents)[0] * 255).astype(np.uint8)

            external_callback(iter, time_left, image)

            self.history["images"].append(image)
            self.image = image

            if self.is_cancelled:
                return False
            else:
                return True
        
        return callback

    def __call__(self, prompt, steps, guidence, seed, external_callback):
        if self.is_generating:
            return
        else:
            self.start_generation()

        self.history["prompt"] = prompt
        self.history["steps"] = steps
        self.history["guidence"] = guidence
        self.history["seed"] = seed

        self.model(
            prompt=prompt,
            height=self.model.height,
            width=self.model.width,
            num_inference_steps=steps,
            guidance_scale=guidence,
            seed=seed,
            callback=self.create_step_callback(external_callback)
        )

        self.end_generation()
