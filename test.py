import cv2
import numpy as np
import torch
import time
import os
import sys
import argparse
import glob
from PIL import Image
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from networks import get_network
from data import get_loader
import torchvision.transforms as std_trnsf
from utils import joint_transforms as jnt_trnsf
from utils.metrics import MultiThresholdMeasures

def str2bool(s):
    return s.lower() in ('t', 'true', 1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ckpt_dir', help='path to ckpt file',type=str,
            default='./models/pspnet_resnet101_sgd_lr_0.002_epoch_100_test_iou_0.918.pth')
    parser.add_argument('--data_dir', help='path to Figaro1k folder', type=str, default='./data/Figaro1k')
    parser.add_argument('--networks', help='name of neural network', type=str, default='pspnet_resnet101')
    parser.add_argument('--save_dir', default='./overlay',
            help='path to save overlay images, default=None and do not save images in this case')
    parser.add_argument('--use_gpu', type=str2bool, default=True,
            help='True if using gpu during inference')

    args = parser.parse_args()

    ckpt_dir = args.ckpt_dir
    data_dir = args.data_dir
    # img_dir = os.path.join(data_dir, 'Original', 'Testing')
    img_dir = data_dir
    network = args.networks.lower()
    save_dir = args.save_dir
    device = 'cuda' if args.use_gpu else 'cpu'

    assert os.path.exists(ckpt_dir)
    assert os.path.exists(data_dir)
    assert os.path.exists(os.path.split(save_dir)[0])

    if not os.path.exists(save_dir):
            os.mkdir(save_dir)

    # prepare network with trained parameters
    net = get_network(network).to(device)
    state = torch.load(ckpt_dir)
    net.load_state_dict(state['weight'])

    # this is the default setting for train_verbose.py
    test_joint_transforms = jnt_trnsf.Compose([
        jnt_trnsf.Safe32Padding()
    ])

    test_image_transforms = std_trnsf.Compose([
        std_trnsf.ToTensor(),
        std_trnsf.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])

    # transforms only on mask
    mask_transforms = std_trnsf.Compose([
        std_trnsf.ToTensor()
        ])

    imgs = glob.glob(os.path.join(img_dir, '*.*'))
    print('image lens:{}'.format(len(imgs))) 
    with torch.no_grad():
        for i, img_path in enumerate(imgs):
            net.eval()
            img = cv2.imread(img_path)
            print('image shape: {}'.format(img))
            data = test_image_transforms(img)
            data = np.expand_dims(data,axis =0)
            #data = data.to(device) 
            
        #
        #
        #
        # for i, (data, label) in enumerate(test_loader):
        #     print('[{:3d}/{:3d}] processing image... '.format(i+1, len(test_loader)))
        #     net.eval()
        #     data, label = data.to(device), label.to(device)
        #
            # inference
            start = time.time()
            logit = net(data)
            duration = time.time() - start

            # prepare mask
            pred = torch.sigmoid(logit.cpu())[0][0].data.numpy()
            mh, mw = data.size(2), data.size(3)
            mask = pred >= 0.5

            mask_n = np.zeros((mh, mw, 3))
            mask_n[:,:,0] = 255
            mask_n[:,:,0] *= mask

            path = os.path.join(save_dir, "figaro_img_%04d.png" % i)
            image_n = cv2.imread(imgs[i])

            # discard padded area
            ih, iw, _ = image_n.shape

            delta_h = mh - ih
            delta_w = mw - iw

            top = delta_h // 2
            bottom = mh - (delta_h - top)
            left = delta_w // 2
            right = mw - (delta_w - left)

            mask_n = mask_n[top:bottom, left:right, :]

            # addWeighted
            image_n = image_n * 0.5 +  mask_n * 0.5


            # write overlay image
            cv2.imwrite(path,image_n)


