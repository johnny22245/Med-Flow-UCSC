import argparse
import json

# GPU
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "3" 

import torch
from PIL import Image

from llava.model.builder import load_pretrained_model
from llava.mm_utils import get_model_name_from_path, tokenizer_image_token, KeywordsStoppingCriteria
from llava.constants import IMAGE_TOKEN_INDEX, DEFAULT_IMAGE_TOKEN
from llava.conversation import conv_templates


MODEL_PATH = "/home/achowd10/models/llava-med-v1.5-mistral-7b"

_tokenizer = None
_model = None
_image_processor = None
_model_name = None


def get_llava_components():
    global _tokenizer, _model, _image_processor, _model_name

    if _model is not None:
        return _tokenizer, _model, _image_processor, _model_name

    model_name = get_model_name_from_path(MODEL_PATH)
    tokenizer, model, image_processor, _ = load_pretrained_model(
        model_path=MODEL_PATH,
        model_base=None,
        model_name=model_name,
        device_map="auto",
    )

    model.to(torch.float16)

    _tokenizer = tokenizer
    _model = model
    _image_processor = image_processor
    _model_name = model_name
    return _tokenizer, _model, _image_processor, _model_name


def crop_from_box(image: Image.Image, box: dict | None, padding: int = 12) -> Image.Image:
    if not box:
        return image

    w, h = image.size
    xmin = max(0, int(box["xmin"]) - padding)
    ymin = max(0, int(box["ymin"]) - padding)
    xmax = min(w, int(box["xmax"]) + padding)
    ymax = min(h, int(box["ymax"]) + padding)

    if xmin >= xmax or ymin >= ymax:
        return image

    return image.crop((xmin, ymin, xmax, ymax))


def generate_summary(image_path: str, use_case: str, crop_box: dict | None) -> str:
    tokenizer, model, image_processor, _ = get_llava_components()

    image = Image.open(image_path).convert("RGB")
    #image = crop_from_box(image, crop_box)

    if use_case == "skin":
        prompt = (
            "Describe the main dermatology finding in this medical image in 2 to 3 short "
            "clinical sentences. Focus on visible lesion characteristics only. "
            "Do not mention treatment. Do not invent unsupported details."
        )
    else:
        prompt = (
            "Describe the main radiology finding in this medical image in 2 to 3 short "
            "clinical sentences. Focus on the visible abnormality only. "
            "Do not mention treatment. Do not invent measurements."
        )

    image_tensor = image_processor.preprocess(
        image, return_tensors="pt"
    )["pixel_values"].half().cuda()

    conv = conv_templates["mistral_instruct"].copy()
    inp = DEFAULT_IMAGE_TOKEN + "\n" + prompt
    conv.append_message(conv.roles[0], inp)
    conv.append_message(conv.roles[1], None)
    prompt_text = conv.get_prompt()

    input_ids = tokenizer_image_token(
        prompt_text,
        tokenizer,
        IMAGE_TOKEN_INDEX,
        return_tensors="pt",
    ).unsqueeze(0).cuda()

    stop_str = conv.sep2
    stopping_criteria = KeywordsStoppingCriteria([stop_str], tokenizer, input_ids)

    with torch.inference_mode():
        output_ids = model.generate(
            input_ids,
            images=image_tensor,
            do_sample=True,
            temperature=0.2,
            max_new_tokens=256,
            use_cache=True,
            stopping_criteria=[stopping_criteria],
        )

    outputs = tokenizer.decode(output_ids[0, input_ids.shape[1]:]).strip()
    if outputs.endswith(stop_str):
        outputs = outputs[:-len(stop_str)].strip()

    return outputs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_json", required=True)
    args = parser.parse_args()

    with open(args.input_json, "r") as f:
        payload = json.load(f)

    text = generate_summary(
        image_path=payload["image_path"],
        use_case=payload.get("use_case", "brain"),
        crop_box=payload.get("crop_box"),
    )

    print(text)


if __name__ == "__main__":
    main()