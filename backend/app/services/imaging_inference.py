import json
import os
import uuid
import subprocess
from typing import Dict, Optional

import numpy as np
import torch
from PIL import Image
from torchvision import transforms

from app.services.LlavaMed_Unet.model import UNet


MODEL_ROOT = "/home/achowd10/MedFlow-244-Project/Med-Flow-UCSC/backend/LlavaMed-Unet"
BRAIN_MODEL_PATH = os.path.join(MODEL_ROOT, "unet_brain_best.pth")
SKIN_MODEL_PATH = os.path.join(MODEL_ROOT, "unet_skin_best.pth")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


_brain_model = None
_skin_model = None

### LLava Med model ###

import json
import os
import subprocess
import tempfile

LLAVA_ENV_NAME = os.getenv("MEDFLOW_LLAVA_ENV", "llava_med")
LLAVA_RUNNER = os.getenv(
    "MEDFLOW_LLAVA_RUNNER",
    "/home/achowd10/MedFlow-244-Project/Med-Flow-UCSC/backend/LlavaMed-Unet/run_llava_med_summary.py",
)


def _scale_box_to_original(ai_box: Optional[dict], model_size: dict, original_size: dict) -> Optional[dict]:
    if not ai_box:
        return None

    mw = model_size["width"]
    mh = model_size["height"]
    ow = original_size["width"]
    oh = original_size["height"]

    sx = ow / mw
    sy = oh / mh

    return {
        "xmin": int(round(ai_box["xmin"] * sx)),
        "ymin": int(round(ai_box["ymin"] * sy)),
        "xmax": int(round(ai_box["xmax"] * sx)),
        "ymax": int(round(ai_box["ymax"] * sy)),
    }


def run_llava_med_summary(
    image_path: str,
    use_case: str,
    predicted_box: Optional[dict],
    original_size: Optional[dict] = None,
    model_size: Optional[dict] = None,
) -> str:
    crop_box = None
    if predicted_box and original_size and model_size:
        crop_box = _scale_box_to_original(
            predicted_box,
            model_size=model_size,
            original_size=original_size,
        )

    payload = {
        "image_path": image_path,
        "use_case": use_case,
        "crop_box": crop_box,
    }

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(payload, f)
            payload_path = f.name

        cmd = [
            "conda",
            "run",
            "-n",
            LLAVA_ENV_NAME,
            "python",
            LLAVA_RUNNER,
            "--input_json",
            payload_path,
        ]

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=240,
            check=True,
        )

        text = (proc.stdout or "").strip()
        if text:
            return text

    except Exception as e:
        print(f"[LLaVA-Med bridge] failed: {e}")

    finally:
        try:
            if "payload_path" in locals() and os.path.exists(payload_path):
                os.remove(payload_path)
        except Exception:
            pass

    if predicted_box:
        if use_case == "skin":
            return (
                "AI review suggests a focal skin lesion region was detected. "
                "Please correlate clinically and confirm lesion margins before diagnosis."
            )
        return (
            "AI review suggests a focal intracranial abnormality was detected in the uploaded scan. "
            "Please confirm the highlighted region and correlate with formal imaging interpretation."
        )

    return (
        "AI review did not identify a confident focal region in this image. "
        "Please review manually before proceeding."
    )

## End of Llava Med model code ##


def is_image_file(filename: str) -> bool:
    ext = os.path.splitext(filename.lower())[1]
    return ext in _IMAGE_EXTS


def detect_use_case(report: dict) -> str:
    """
    Stable routing for demo:
    - explicit metadata first
    - then filename heuristics
    - fallback brain
    """
    test_code = (report.get("test_code") or "").lower()
    filename = (report.get("filename") or "").lower()

    if "skin" in test_code or "derm" in test_code or "lesion" in test_code:
        return "skin"

    if "skin" in filename or "lesion" in filename or "derm" in filename:
        return "skin"

    return "brain"


def _load_unet(model_path: str, in_channels: int, out_classes: int = 2):
    model = UNet(in_channels=in_channels, out_classes=out_classes)
    state = torch.load(model_path, map_location=DEVICE)
    model.load_state_dict(state)
    model.to(DEVICE)
    model.eval()
    return model


def get_brain_model():
    global _brain_model
    if _brain_model is None:
        _brain_model = _load_unet(BRAIN_MODEL_PATH, in_channels=1)
    return _brain_model


def get_skin_model():
    global _skin_model
    if _skin_model is None:
        _skin_model = _load_unet(SKIN_MODEL_PATH, in_channels=3)
    return _skin_model


def _brain_transform():
    return transforms.Compose([
        transforms.Grayscale(num_output_channels=1),
        transforms.Resize((256, 256)),
        transforms.ToTensor(),
    ])


def _skin_transform():
    return transforms.Compose([
        transforms.Resize((256, 256)),
        transforms.ToTensor(),
    ])


def _predict_mask(image_path: str, use_case: str) -> np.ndarray:
    if use_case == "skin":
        model = get_skin_model()
        img = Image.open(image_path).convert("RGB")
        tensor = _skin_transform()(img).unsqueeze(0).to(DEVICE)
    else:
        model = get_brain_model()
        img = Image.open(image_path).convert("L")
        tensor = _brain_transform()(img).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        output = model(tensor)
        pred = torch.argmax(output, dim=1).squeeze(0).cpu().numpy().astype(np.uint8)

    return pred


def _bbox_from_mask(mask: np.ndarray) -> Optional[Dict[str, int]]:
    if not np.any(mask == 1):
        return None

    y_idx, x_idx = np.where(mask == 1)
    ymin, ymax = int(np.min(y_idx)), int(np.max(y_idx))
    xmin, xmax = int(np.min(x_idx)), int(np.max(x_idx))
    return {
        "xmin": xmin,
        "ymin": ymin,
        "xmax": xmax,
        "ymax": ymax,
    }


def _normalized_box(box: Optional[Dict[str, int]], width: int, height: int):
    if not box or width <= 0 or height <= 0:
        return None

    return {
        "xmin": round(box["xmin"] / width, 6),
        "ymin": round(box["ymin"] / height, 6),
        "xmax": round(box["xmax"] / width, 6),
        "ymax": round(box["ymax"] / height, 6),
    }


def _save_mask(mask: np.ndarray, patient_id: str, original_filename: str) -> str:
    out_dir = os.path.join("data", "reports", patient_id)
    os.makedirs(out_dir, exist_ok=True)

    stem, _ = os.path.splitext(original_filename)
    mask_name = f"{stem}_ai_mask_{uuid.uuid4().hex[:8]}.png"
    mask_path = os.path.join(out_dir, mask_name)

    Image.fromarray((mask * 255).astype(np.uint8)).save(mask_path)
    return f"/reports/{patient_id}/{mask_name}"



def analyze_uploaded_image(patient_id: str, report: dict) -> dict:
    filename = report.get("filename")
    rel_path = report.get("path")

    if not filename or not rel_path:
        raise ValueError("Uploaded report is missing filename or path.")

    if not os.path.exists(rel_path):
        raise FileNotFoundError(f"Image file not found: {rel_path}")

    if not is_image_file(filename):
        raise ValueError("Selected report is not an image file.")

    use_case = detect_use_case(report)
    pil_img = Image.open(rel_path)
    original_w, original_h = pil_img.size

    mask = _predict_mask(rel_path, use_case)
    resized_h, resized_w = mask.shape[:2]

    ai_box = _bbox_from_mask(mask)
    ai_box_norm = _normalized_box(ai_box, resized_w, resized_h)
    mask_url = _save_mask(mask, patient_id, filename)
    llava_summary = run_llava_med_summary(
                        rel_path,
                        use_case,
                        ai_box,
                        original_size={"width": original_w, "height": original_h},
                        model_size={"width": resized_w, "height": resized_h},
                    )

    return {
        "report_filename": filename,
        "report_url": report.get("url") or f"/reports/{patient_id}/{filename}",
        "use_case": use_case,
        "image_size_original": {"width": original_w, "height": original_h},
        "image_size_model": {"width": resized_w, "height": resized_h},
        "ai_box": ai_box,
        "ai_box_normalized": ai_box_norm,
        "clinician_box": ai_box,
        "mask_url": mask_url,
        "llava_summary": llava_summary,
        "status": "ai_detected" if ai_box else "no_finding",
    }