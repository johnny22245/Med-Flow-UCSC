import torch
import torch.nn as nn

import os
os.environ["CUDA_VISIBLE_DEVICES"] = "3" 

class DoubleConv(nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.double_conv = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )

    def forward(self, x):
        return self.double_conv(x)

class UNet(nn.Module):
    # out_classes=2 for Background (0) and Tumor (1)
    def __init__(self, in_channels=1, out_classes=2, base_features=64):
        super().__init__()
        
        self.down1 = DoubleConv(in_channels, base_features)
        self.pool1 = nn.MaxPool2d(2)
        self.down2 = DoubleConv(base_features, base_features * 2)
        self.pool2 = nn.MaxPool2d(2)
        self.down3 = DoubleConv(base_features * 2, base_features * 4)
        self.pool3 = nn.MaxPool2d(2)
        
        self.bottleneck = DoubleConv(base_features * 4, base_features * 8)
        
        self.upConv1 = nn.ConvTranspose2d(base_features * 8, base_features * 4, kernel_size=2, stride=2)
        self.up1 = DoubleConv(base_features * 8, base_features * 4)
        
        self.upConv2 = nn.ConvTranspose2d(base_features * 4, base_features * 2, kernel_size=2, stride=2)
        self.up2 = DoubleConv(base_features * 4, base_features * 2)
        
        self.upConv3 = nn.ConvTranspose2d(base_features * 2, base_features, kernel_size=2, stride=2)
        self.up3 = DoubleConv(base_features * 2, base_features)
        
        self.out_conv = nn.Conv2d(base_features, out_classes, kernel_size=1)

    def forward(self, x):
        d1 = self.down1(x)
        p1 = self.pool1(d1)
        d2 = self.down2(p1)
        p2 = self.pool2(d2)
        d3 = self.down3(p2)
        p3 = self.pool3(d3)
        
        bn = self.bottleneck(p3)
        
        u1 = self.upConv1(bn)
        u1 = torch.cat([u1, d3], dim=1)
        u1 = self.up1(u1)
        
        u2 = self.upConv2(u1)
        u2 = torch.cat([u2, d2], dim=1)
        u2 = self.up2(u2)
        
        u3 = self.upConv3(u2)
        u3 = torch.cat([u3, d1], dim=1)
        u3 = self.up3(u3)
        
        return self.out_conv(u3)