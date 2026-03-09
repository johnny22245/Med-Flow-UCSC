import os
import torch
from llava.model.builder import load_pretrained_model
from llava.mm_utils import get_model_name_from_path, tokenizer_image_token, KeywordsStoppingCriteria
from llava.constants import IMAGE_TOKEN_INDEX, DEFAULT_IMAGE_TOKEN
from llava.conversation import conv_templates
from PIL import Image
import requests
from io import BytesIO

# 1. IMPORT YOUR PREDICT FUNCTIONS
from predict import predict_tumor
from predict_skin import predict_skin_lesion

def run_inference(image_url="Brains/predictions/1 copy.png"):
    model_path = "microsoft/llava-med-v1.5-mistral-7b"
    model_name = get_model_name_from_path(model_path)
    
    print(f"--- Loading Model: {model_name} ---")
    
    tokenizer, model, image_processor, context_len = load_pretrained_model(
        model_path=model_path,
        model_base=None,
        model_name=model_name,
        device_map="auto"
    )

    model.to(torch.float16)

    prompt = "Describe the findings in this medical image."
    
    # 2. LOAD AND SAVE THE IMAGE LOCALLY
    local_image_path = "temp_llava_eval_image.png"
    
    if image_url.startswith('http'):
        response = requests.get(image_url)
        image = Image.open(BytesIO(response.content)).convert('RGB')
    else:
        image = Image.open(image_url).convert('RGB')
        
    # Save the image so the U-Nets can open it
    image.save(local_image_path)

    image_tensor = image_processor.preprocess(image, return_tensors='pt')['pixel_values'].half().cuda()

    conv = conv_templates["mistral_instruct"].copy()
    inp = DEFAULT_IMAGE_TOKEN + '\n' + prompt
    conv.append_message(conv.roles[0], inp)
    conv.append_message(conv.roles[1], None)
    prompt_text = conv.get_prompt()

    input_ids = tokenizer_image_token(prompt_text, tokenizer, IMAGE_TOKEN_INDEX, return_tensors='pt').unsqueeze(0).cuda()
    
    stop_str = conv.sep2
    keywords = [stop_str]
    stopping_criteria = KeywordsStoppingCriteria(keywords, tokenizer, input_ids)

    print(f"\n--- Model Analyzing Image ---\n")
    with torch.inference_mode():
        output_ids = model.generate(
            input_ids,
            images=image_tensor,
            do_sample=True,
            temperature=0.2,
            max_new_tokens=512,
            use_cache=True,
            stopping_criteria=[stopping_criteria]
        )

    outputs = tokenizer.decode(output_ids[0, input_ids.shape[1]:]).strip()
    if outputs.endswith(stop_str):
        outputs = outputs[:-len(stop_str)]
    
    print(f"Question: {prompt}")
    print(f"Answer: {outputs}\n")

    # 3. PARSE LLaVA'S OUTPUT TO ROUTE TO THE CORRECT U-NET SPECIALIST
    outputs_lower = outputs.lower()
    
    # Define Brain Trigger Words
    brain_keywords = ["brain", "cerebral", "mri", "head"]
    brain_tumor_keywords = ["tumor", "mass", "lesion", "glioma", "meningioma", "neoplasm", "cancer"]
    
    # Define Skin Trigger Words
    skin_keywords = ["skin", "dermoscopy", "dermatology", "epidermis", "cutaneous"]
    skin_lesion_keywords = ["lesion", "melanoma", "nevus", "mole", "carcinoma", "cancer", "tumor"]
    
    # Check LLaVA's context
    is_brain = any(word in outputs_lower for word in brain_keywords)
    has_brain_tumor = any(word in outputs_lower for word in brain_tumor_keywords)
    
    is_skin = any(word in outputs_lower for word in skin_keywords)
    has_skin_lesion = any(word in outputs_lower for word in skin_lesion_keywords)
    
    # Route the image based on the findings
    if is_brain and has_brain_tumor:
        print(">>> ALERT: LLaVA detected a potential brain tumor.")
        print(">>> Triggering Brain U-Net Segmentation Specialist...\n")
        
        predict_tumor(
            image_path=local_image_path, 
            model_weights_path='unet_brain_best.pth', 
            device='cuda',
            target_size=(256, 256)
        )
        
    elif is_skin and has_skin_lesion:
        print(">>> ALERT: LLaVA detected a potential skin lesion.")
        print(">>> Triggering Skin U-Net Segmentation Specialist...\n")
        
        predict_skin_lesion(
            image_path=local_image_path, 
            model_weights_path='unet_skin_best.pth', 
            device='cuda',
            target_size=(256, 256)
        )
        
    else:
        print(">>> LLaVA did not detect a critical brain tumor or skin lesion. Skipping segmentation.")

if __name__ == "__main__":
    # You can now easily swap this string to test different modalities
    test_image = "Brains/predictions/1 copy.png"
    # test_image = "Skin/predictions/1.png"
    run_inference(test_image)