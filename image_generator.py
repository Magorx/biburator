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
            "negative_prompt": None,
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
        image.save(path)

        self.logger.info("image saved to " + str(path))

    def save_history(self):
        path = self.generate_image_path() + '.gif'
    
        images = [PIL.Image.fromarray(img) for img in self.history['images']]
        images[0].save(path, save_all=True, append_images=images[1:], duration=self.history_frame_duration)
    
        self.logger.info("history saved to " + str(path))

    def generate_image_path(self):
        prompt = self.history['prompt']
        negative_prompt = self.history['negative_prompt']

        if prompt is None:
            prompt = ""
        if negative_prompt is None:
            negative_prompt = ""
        
        prompt = prompt.replace('/', '_').replace(', ', ',').replace('. ', ',').replace(' ', '_')
        negative_prompt = negative_prompt.replace('/', '_').replace(', ', ',').replace('. ', ',').replace(' ', '_')

        if len(prompt) + len(negative_prompt) > 50:
            lens_proportions = len(prompt) / (len(prompt) + len(negative_prompt))
            prompt = prompt[:int(50 * lens_proportions)]
            negative_prompt = negative_prompt[:int(50 * (1 - lens_proportions))]
        
        text = prompt + "," + negative_prompt
        text = text.split(',')
    
        folder = os.path.join(self.args.o, '_'.join(text))
        os.makedirs(folder, exist_ok=True)

        name = f"{self.history['seed']}_{len(self.history['images'])}_{self.history['guidence']}".replace(".", "_")
        return os.path.join(folder, name)

    def create_step_callback(self, external_callback):
        def callback(iter, time_left, latents):
            if latents is None:
                if self.history_frame_duration < 1:
                    image = (np.ones((512, 512, 3)) * np.random.random() * 255).astype(np.uint8)
                else:
                    image = (np.random.random((512, 512, 3)) * 255).astype(np.uint8)
            else:
                if self.history_frame_duration < 1:
                    image = latents
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

    def __call__(self, prompt, negative_prompt, steps, guidence, seed, external_callback):
        if self.is_generating:
            return
        else:
            self.start_generation()

        self.history["prompt"] = prompt
        self.history["negative_prompt"] = negative_prompt
        self.history["steps"] = steps
        self.history["guidence"] = guidence
        self.history["seed"] = seed

        self.model(
            prompt=prompt,
            negative_prompt=negative_prompt,
            height=self.model.height,
            width=self.model.width,
            num_inference_steps=steps,
            guidance_scale=guidence,
            seed=seed,
            callback=self.create_step_callback(external_callback)
        )

        self.end_generation()
