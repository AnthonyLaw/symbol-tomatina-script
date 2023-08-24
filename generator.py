from PIL import Image

def generate_images_nft(filenames, output_filename):
    """
    Stack multiple PNG images on top of each other, like layering in NFT art.

    Parameters:
    - filenames: List of paths to PNG images to stack.
    - output_filename: Path where the stacked image will be saved.
    """

    # Open the first image
    stacked_img = Image.open(filenames[0])

    # Iterate over the other images and paste them on top
    for filename in filenames[1:]:
        img = Image.open(filename)
        stacked_img.paste(img, (0, 0), img)  # The last parameter is the alpha mask for transparency

    # Save the stacked image
    stacked_img.save(output_filename)
