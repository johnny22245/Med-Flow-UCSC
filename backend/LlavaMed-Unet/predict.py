import torch
import torch.nn.functional as F
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image, ImageDraw # NEW: ImageDraw added
from model import UNet

def predict_tumor(image_path, model_weights_path='unet_brain_best.pth', device='cuda', target_size=(256, 256)):
    # 1. Initialize the Binary Model (out_classes=2)
    device = torch.device(device if torch.cuda.is_available() else 'cpu')
    model = UNet(in_channels=1, out_classes=2, base_features=64).to(device)
    
    try:
        state_dict = torch.load(model_weights_path, map_location=device, weights_only=True)
    except FileNotFoundError:
        print(f"Error: Could not find '{model_weights_path}'.")
        return

    if list(state_dict.keys())[0].startswith('module.'):
        state_dict = {k[7:]: v for k, v in state_dict.items()}
        
    model.load_state_dict(state_dict)
    model.eval()

    # 2. Load and preprocess the PNG
    try:
        raw_img = Image.open(image_path).convert('L') 
    except FileNotFoundError:
        print(f"Error: Could not find '{image_path}'.")
        return

    img_array = np.array(raw_img, dtype=np.float32)
    min_val, max_val = np.min(img_array), np.max(img_array)
    if max_val - min_val > 0:
        img_array = (img_array - min_val) / (max_val - min_val)

    img_tensor = torch.tensor(img_array).unsqueeze(0).unsqueeze(0)
    img_tensor = F.interpolate(img_tensor, size=target_size, mode='bilinear', align_corners=False)
    img_tensor = img_tensor.to(device)

    # 3. Run Inference
    with torch.no_grad():
        output = model(img_tensor)
        probabilities = torch.softmax(output, dim=1)
        
        print("\n--- Model Confidence Report ---")
        print(f"Max confidence for Background:  {probabilities[0, 0].max().item() * 100:.2f}%")
        print(f"Max confidence for Brain Tumor: {probabilities[0, 1].max().item() * 100:.2f}%\n")

        prediction = torch.argmax(output, dim=1).squeeze(0).cpu().numpy()

    # 4. Save the Mask as Pure White (255) for visibility
    mask_image = Image.fromarray((prediction * 255).astype(np.uint8))
    mask_save_name = image_path.replace(".png", "_tumor_mask.png")
    mask_image.save(mask_save_name)
    print(f"Saved predicted tumor mask to '{mask_save_name}'")

    original_resized = img_tensor.squeeze().cpu().numpy()

    # 5. --- NEW: Save the Image with the Bounding Box ---
    # Check if a tumor was predicted
    if np.any(prediction == 1):
        y_indices, x_indices = np.where(prediction == 1)
        ymin, ymax = np.min(y_indices), np.max(y_indices)
        xmin, xmax = np.min(x_indices), np.max(x_indices)
        
        # Convert the normalized 2D array back to a standard RGB image so we can draw a red line
        rgb_image = Image.fromarray((original_resized * 255).astype(np.uint8)).convert("RGB")
        draw = ImageDraw.Draw(rgb_image)
        
        # Draw the rectangle [left, top, right, bottom]
        draw.rectangle([xmin, ymin, xmax, ymax], outline="red", width=2)
        
        box_save_name = image_path.replace(".png", "_bounding_box.png")
        rgb_image.save(box_save_name)
        print(f"Saved bounding box image to '{box_save_name}'\n")
    else:
        print("No tumor detected, skipping bounding box creation.\n")
    # ----------------------------------------------------

    # 6. Visualize in the pop-up window
    from matplotlib.colors import ListedColormap
    cmap = ListedColormap(['black', 'red'])

    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    
    axes[0].imshow(original_resized, cmap='gray')
    axes[0].set_title(f"Input MRI Slice {target_size}")
    axes[0].axis('off')
    
    # Add the rectangle to the plot as well
    if np.any(prediction == 1):
        box_width = xmax - xmin
        box_height = ymax - ymin
        rect = patches.Rectangle((xmin, ymin), box_width, box_height, 
                                 linewidth=2, edgecolor='red', facecolor='none')
        axes[0].add_patch(rect)

    axes[1].imshow(prediction, cmap=cmap, vmin=0, vmax=1)
    axes[1].set_title("Predicted Brain Tumor Mask")
    axes[1].axis('off')

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    # Point this to a test PNG from your dataset
    test_image_path = "Brains/predictions/1.png" 
    predict_tumor(test_image_path)