import matplotlib
font = {'family': 'arial',
        'size': 14}

matplotlib.rc('font', **font)
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle, Circle



def read_file(filename):
    f = open(filename, 'r')
    data_list = []
    for line in f.readlines():
        split = line.split(',')
        if len(split) == 6:
            try:
                data_list.append([float(x) for x in split])
            except ValueError:
                pass

    return data_list


def padded_matrix(xc, yc, values, step_x, step_y):
    xsteps = xc.max() - xc.min() + 2
    x_linspace = np.linspace(xc.min(), xc.max() + 1, xsteps)
    x_linspace = (x_linspace - 0.5) * step_x
    ysteps = yc.max() - yc.min() + 2
    y_linspace = np.linspace(yc.min(), yc.max() + 1, ysteps)
    y_linspace = (y_linspace - 0.5) * step_y
    X, Y = np.meshgrid(x_linspace, y_linspace)
    V = np.zeros([int(xsteps) - 1 , int(ysteps) - 1])
    x_indices = xc - xc.min()
    y_indices = yc - yc.min()
    for x, y, mag in zip(x_indices, y_indices, values):
        V[int(x), int(y)] = mag
    return X, Y, V


def unpadded_matrix(xc, yc, values, step_x, step_y):
    xsteps = xc.max() - xc.min() + 1
    x_linspace = np.linspace(xc.min(), xc.max(), xsteps)
    x_linspace = x_linspace * step_x
    ysteps = yc.max() - yc.min() + 1
    y_linspace = np.linspace(yc.min(), yc.max(), ysteps)
    y_linspace = y_linspace * step_y
    X, Y = np.meshgrid(x_linspace, y_linspace)
    V = np.zeros([int(xsteps), int(ysteps)])
    x_indices = xc - xc.min()
    y_indices = yc - yc.min()
    for x, y, mag in zip(x_indices, y_indices, values):
        V[int(x), int(y)] = mag
    return X, Y, V


def prep_data(xydata, changing_axes=None, measure_step=None, interesting_mag='z', normalize=True):
    if measure_step is None:
        measure_step = [0.5, 0.5, 0.5]
    elif isinstance(measure_step, (int, float)):
        measure_step = [measure_step, measure_step, measure_step]
    xydata = np.asarray(xydata)
    coords = xydata[:, 0:3]
    try:
        interesting_mag = 'xyz'.index(interesting_mag)
    except ValueError:
        raise ValueError('mag axis need to be either of x y z.')
    mags = np.abs(xydata[:, 3 + interesting_mag])
    if normalize:
        mags = mags / (mags[int((len(mags) - 1) / 2)])
    try:
        xaxis = 'xyz'.index(changing_axes[0])
        yaxis = 'xyz'.index(changing_axes[1])
    except (IndexError, ValueError):
        raise ValueError('Invalid axes specifier: %s' % changing_axes)
    if coords[:, xaxis].min() == coords[:, xaxis].max():
        raise ValueError('provided figure x axis is constant across measured values.')
    if coords[:, yaxis].min() == coords[:, yaxis].max():
        raise ValueError('provided figure x axis is constant across measured values.')
    x_coords = coords[:, xaxis]
    y_coords = coords[:, yaxis]
    xstep = measure_step[xaxis]
    ystep = measure_step[yaxis]
    return x_coords, y_coords, xstep, ystep, mags


def plot_intensity(data, axes=None, unit='nT', step_length=None, mag_axis='z', normalize=True):
    x_coords, y_coords, xstep, ystep, mags = prep_data(data, changing_axes=axes, measure_step=step_length,
                                                       interesting_mag=mag_axis, normalize=normalize)

    X, Y, colors = padded_matrix(x_coords, y_coords, mags, xstep, ystep)
    f, ax = plt.subplots(1)
    ax.set_aspect(1)
    ax.set_xlabel('Distance from center/cm, %s axis' % axes[0])
    ax.set_ylabel('Distance from center/cm, %s axis' % axes[1])
    p = ax.pcolormesh(X, Y, colors, cmap='jet')
    cbar = f.colorbar(p)
    if normalize:
        cbar.ax.set_ylabel('Relative magnetic field strength')
    else:
        cbar.ax.set_ylabel('Magnetic field strength/%s' % unit)
    return f, ax


def plot_gradient(data, axes, step_length, mag_axis):
    x_coords, y_coords, xstep, ystep, mags = prep_data(data, changing_axes=axes, measure_step=step_length,
                                                       interesting_mag=mag_axis, normalize=True)
    X, Y, values = unpadded_matrix(x_coords, y_coords, mags, xstep, ystep)
    gradient = np.gradient(values, ystep, axis=0)
    f, ax = plt.subplots(1)
    ax.set_aspect(1)
    ax.set_xlabel('Distance from center/cm, %s axis' % axes[0])
    ax.set_ylabel('Distance from center/cm, %s axis' % axes[1])
    cs = ax.contour(X, Y, np.abs(gradient), [0.0005, 0.001, 0.002, 0.004], colors='w', zorder=10)
    csf = ax.contourf(X, Y, np.abs(gradient), 21, cmap='inferno')
    ax.clabel(cs, fontsize=11, inline=1, fmt='%.4f')

    cbar = f.colorbar(csf)
    cbar.ax.set_ylabel('Field strength gradient/cm')
    return f, ax


def draw_rectangle_cell(ax, width, height):
    r = Rectangle([-width/2, -height/2], width, height, fill=False, linewidth=1, edgecolor='w', linestyle='--')
    ax.plot(0, 0, 'b+', color='w')
    ax.add_artist(r)
    return r


def draw_circular_cell(ax, diameter):
    c = Circle([0, 0], diameter/2, fill=False, linewidth=1, edgecolor='w', linestyle='--')
    ax.plot(0, 0, 'b+', color='w')
    ax.add_artist(c)
    return c