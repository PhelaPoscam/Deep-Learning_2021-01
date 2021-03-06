import os
import json
import string
import click
import cv2
import torch

# from torchvision.transforms import Compose
from dataset.data_transform import Resize, Rotation, Translation, Scale
from dataset.text_data import TextDataset
from dataset.my_collate import text_collate
from dataset.predict_dataset import PredictDataset

from albumentations import *

from torch.autograd import Variable
from torch.utils.data import DataLoader

from test import test
from models.model_loader import load_model
from tqdm import tqdm

import matplotlib.pyplot as plt
import numpy as np


def recognize_characters(images, model_path):
    # configurations
    # model parameters
    ABC = "ABCEHIKMOPTX0123456789"
    seq_proj = (32, 32)
    input_size = (1, 20)
    cuda = False

    # fit parameters
    transform = Compose([
        Rotate(limit=15, p=0.01),
        # MedianBlur(blur_limit=3, p=1),
        # GaussNoise(var_limit=(3, 3), p=1),
        Normalize(),
        Resize(input_size[0], input_size[1], always_apply=True),
    ])

    # load data set
    data = PredictDataset(images, None)

    # load model
    model = load_model(ABC, seq_proj, "resnet18", model_path, cuda).eval()

    # make predictions
    data_loader = DataLoader(data, batch_size=1, num_workers=4, shuffle=False, collate_fn=text_collate)
    predicted_charcters = []
    for item in tqdm(data_loader):
        imgs = Variable(item["img"])
        out = model(imgs, decode=True)
        predicted_character = out[0]
        predicted_charcters.append(predicted_character)

    return "".join(predicted_charcters)


def text_to_seq(self, text):
    seq = []
    for c in text:
        seq.append(self.config["abc"].find(c) + 1)
    return seq


@click.command()
@click.option('--model-path', type=str, default=None, nargs=1, help='Path to pretrained model')
@click.option('--data-path', type=str, default=None, nargs=1, help='Path to images')
@click.option('--input-size', type=str, default="32x32", help='Alphabet')
@click.option('--abc', type=str, default=string.ascii_uppercase + string.digits, help='Input size')
@click.option('--seq-proj', type=str, default="1x20", help='Projection of sequence')
def main(model_path, data_path, input_size, abc, seq_proj):
    seq_proj = [int(x) for x in seq_proj.split('x')]
    cuda = False
    # model = model.eval()

    input_size = [int(x) for x in input_size.split('x')]
    transform = Compose([
        Rotate(limit=15, p=0.01),
        # MedianBlur(blur_limit=3, p=1),
        # GaussNoise(var_limit=(3, 3), p=1),
        Normalize(),
        Resize(input_size[0], input_size[1], always_apply=True),
    ])
    # create_desc_file(data_path, abc)
    data = TextDataset(data_path=data_path, mode="test", transform=transform)
    model = load_model(data.get_abc(), seq_proj, "resnet18", model_path, cuda).eval()
    acc = predict(model, data)
    print(f"Acc:{acc}")


def create_desc_file(path, abc):
    with open(os.path.join(path, "desc.json"), 'w') as f:
        content = {"abc": abc, "train": [], "test": []}
        for filename in os.listdir(os.path.join(path, "data")):
            item = {"name": "data/" + filename, "text": filename[:filename.rfind('.')]}
            content["test"].append(item)
        json.dump(content, f)


def predict(model, data):
    visualize = True
    data_loader = DataLoader(data, batch_size=1, num_workers=4, shuffle=False, collate_fn=text_collate)
    count = 0
    tp = 0
    abc = data.get_abc()
    for item in tqdm(data_loader):
        imgs = Variable(item["img"])
        out = model(imgs, decode=True)
        gt = (item["seq"].numpy() - 1).tolist()
        actual = ''.join(abc[c] for c in gt)
        pred = out[0]
        if visualize:
            img = imgs[0].permute(1, 2, 0).cpu().data.numpy().astype(np.uint8)
            plt.imshow(img)
            plt.show()
            print(f"PREDICTION: {pred}")
        if str(pred) == str(actual):
            tp += 1
        count += 1
    return tp / count


if __name__ == "__main__":
    #main()
    image = cv2.imread("/home/vosar/Documents/CS@UCU/AI/CourseProject/datasets/dataset-real-plates-500-10000/data/0_AA0000AA_2.jpg")
    print(recognize_characters([image], "recognition/crnn-pytorch/out/crnn_resnet18_ABCEHIKMOPTX0123456789_best"))
