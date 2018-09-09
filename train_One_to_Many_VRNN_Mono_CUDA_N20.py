import math
import torch
import torch.nn as nn
import torch.utils
import torch.utils.data
from torchvision import datasets, transforms
from torch.autograd import Variable
import matplotlib.pyplot as plt 
from model_VRNN_CUDA import VRNN
import os
from frames_dataset import FramesDataset_Mono
from matplotlib import animation
import numpy as np


import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.path as path

"""implementation of the Variational Recurrent
Neural Network (VRNN) from https://arxiv.org/abs/1506.02216
using unimodal isotropic gaussian distributions for 
inference, prior, and generating models."""


def train_at_all(epoch, data_all):
    train_loss = 0

    #forward + backward + optimize
    optimizer.zero_grad()
    kld_loss, nll_loss, _, _ = model(data_all)
    loss = kld_loss + nll_loss
    loss.backward()
    optimizer.step()

    #grad norm clipping, only in pytorch version >= 1.10
    nn.utils.clip_grad_norm(model.parameters(), clip)

    train_loss += loss.data[0]

    print('====> Epoch: {} Average loss: {:.4f}'.format(
         epoch, train_loss / len(train_loader.dataset)))

    return

def train(epoch):
    train_loss = 0
    for batch_idx, data in enumerate(train_loader):

        #transforming data
        #data = Variable(data)
        #to remove eventually
        data = Variable(torch.unsqueeze(data['frame'],1)).float().cuda()
        data = (data - data.min().data[0]) / (data.max().data[0] - data.min().data[0])

        #forward + backward + optimize
        optimizer.zero_grad()
        kld_loss, nll_loss, _, _ = model(data)
        loss = kld_loss + nll_loss
        loss.backward()
        optimizer.step()

        #grad norm clipping, only in pytorch version >= 1.10
        nn.utils.clip_grad_norm(model.parameters(), clip)

        #sample = model.sample(batch_size, 14)
        #print('sample')
        #print(sample)
        #plt.imshow(sample.numpy())
        #plt.pause(1e-6)

        #printing
        if batch_idx % print_every == 0:
            print('Train Epoch: {} [{}/{} ({:.0f}%)]\t KLD Loss: {:.6f} \t NLL Loss: {:.6f}'.format(
                epoch, batch_idx * len(data), len(train_loader.dataset),
                100. * batch_idx / len(train_loader),
                kld_loss.data[0] / batch_size,
                nll_loss.data[0] / batch_size))

        train_loss += loss.data[0]

    print('====> Epoch: {} Average loss: {:.4f}'.format(
         epoch, train_loss / len(train_loader.dataset)))

    return


def init():
    plot.set_data(data[0])
    return [plot]


def update(j):
    plt.title(int(j/batch_size))
    plot.set_data(data[j])
    return [plot]

def statistics_update(epoch):
    # simulate new data coming in
    #data = np.random.randn(1000)
    n, bins = np.histogram(statistic_original[epoch], 100)
    top = bottom + n
    verts[1::5, 1] = top
    verts[2::5, 1] = top

    n1, bins1 = np.histogram(statistic_generated[epoch], 100)
    top1 = bottom + n1
    verts1[1::5, 1] = top1
    verts1[2::5, 1] = top1
    return [patch, patch1]


# hyperparameters
torch.cuda.set_device(1)
if torch.cuda.is_available():
    print(torch.cuda.current_device())
    print(torch.cuda.get_device_name(0))
    print(torch.cuda.get_device_name(1))
    print(torch.cuda.get_device_capability(0))
    print(torch.cuda.get_device_capability(1))

h_dim = 100
z_dim = 16
n_layers = 1
n_epochs = 50
clip = 30
learning_rate = 5e-4
batch_size = 120
seed = 128
print_every = 100
save_every = 10

# manual seed
torch.manual_seed(seed)

#plt.ion()

basePath = os.path.dirname(os.path.abspath(__file__))
face_dataset = FramesDataset_Mono(basePath + '/train/annotations_single_bubble.csv', basePath + '/train')
train_loader = torch.utils.data.DataLoader(face_dataset, batch_size=batch_size)

x_dim = face_dataset[0]['frame'].shape[0]

model = VRNN(x_dim, h_dim, z_dim, n_layers)
optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
#model.load_state_dict(torch.load('20_05.pth'))

generate_epoch=1
data = np.empty(batch_size*n_epochs*generate_epoch, dtype=object)
statistic_generated = np.empty((n_epochs, batch_size*generate_epoch), dtype=float)
statistic_original = np.empty((n_epochs, batch_size*generate_epoch), dtype=float)

for epoch in range(1, n_epochs + 1):

    # training + testing
    train(epoch)

    # saving model
    if epoch % save_every == 1:
        fn = 'vrnn_state_dict_'+str(epoch)+'.pth'
        torch.save(model.state_dict(), fn)
        print('Saved model to '+fn)

    # save generated video to memory
    output = model.sample2_reverse(batch_size*generate_epoch)

    # concatenate generated and original video
    for k in range(batch_size*generate_epoch):
        generated = np.resize(output[k].cpu().numpy(),(48,85))
        statistic_generated[epoch-1,k] = generated[10,50]
        original = np.resize(train_loader.dataset[k+(epoch-1)*batch_size*generate_epoch]['frame'] / 255,(48,85))
        statistic_original[epoch-1,k] = original[10,50]
        data[k+batch_size*(epoch-1)] = np.vstack((generated / (np.max(generated) - np.min(generated)), original))


# show generated video
print('show generated video')
fig = plt.figure()
plot = plt.matshow(data[0], cmap='gray', fignum=0)
anim = animation.FuncAnimation(fig, update, init_func=init, frames=batch_size*n_epochs*generate_epoch, interval=30,
                                         blit=True)
plt.show()

# show statictics

# Fixing random state for reproducibility
np.random.seed(19680801)

# histogram our data with numpy
data = statistic_generated[0]
n, bins = np.histogram(data, 100)

# get the corners of the rectangles for the histogram
left = np.array(bins[:-1])
right = np.array(bins[1:])
bottom = np.zeros(len(left))
top = bottom + n
nrects = len(left)


nverts = nrects * (1 + 3 + 1)
verts = np.zeros((nverts, 2))
codes = np.ones(nverts, int) * path.Path.LINETO
codes[0::5] = path.Path.MOVETO
codes[4::5] = path.Path.CLOSEPOLY
verts[0::5, 0] = left
verts[0::5, 1] = bottom
verts[1::5, 0] = left
verts[1::5, 1] = top
verts[2::5, 0] = right
verts[2::5, 1] = top
verts[3::5, 0] = right
verts[3::5, 1] = bottom

nverts1 = nrects * (1 + 3 + 1)
verts1 = np.zeros((nverts, 2))
codes1 = np.ones(nverts, int) * path.Path.LINETO
codes1[0::5] = path.Path.MOVETO
codes1[4::5] = path.Path.CLOSEPOLY
verts1[0::5, 0] = left
verts1[0::5, 1] = bottom
verts1[1::5, 0] = left
verts1[1::5, 1] = top
verts1[2::5, 0] = right
verts1[2::5, 1] = top
verts1[3::5, 0] = right
verts1[3::5, 1] = bottom
patch = None
patch1 = None

fig, ax = plt.subplots(nrows=1, ncols=2)
barpath = path.Path(verts, codes)
patch = patches.PathPatch(
    barpath, facecolor='green', edgecolor='yellow', alpha=0.5)
barpath1 = path.Path(verts1, codes1)
patch1 = patches.PathPatch(
    barpath1, facecolor='red', edgecolor='yellow', alpha=0.5)
ax[0].add_patch(patch)

ax[0].set_xlim(left[0], right[-1])
ax[0].set_ylim(bottom.min(), top.max())
ax[0].set_title('Original')
ax[1].add_patch(patch1)

ax[1].set_xlim(left[0], right[-1])
ax[1].set_ylim(bottom.min(), top.max())
ax[1].set_title('Generated')

ani = animation.FuncAnimation(fig, statistics_update, n_epochs, repeat=True, blit=True, interval=300)
plt.show()