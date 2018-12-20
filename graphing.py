import matplotlib
from scipy.interpolate import griddata
font = {'family': 'arial',
        'size': 14}

matplotlib.rc('font', **font)
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle, Circle


def read_file(filename, cst=False):
    if cst:
        delimiter = None
    else:
        delimiter = ','
    f = open(filename, 'r')
    data_list = []
    for line in f.readlines():
        split = line.split(delimiter)
        if len(split) == 6 or len(split) == 9:
            try:
                data_list.append([float(x) for x in split[0:6]])
            except ValueError:
                pass

    return np.array(data_list)


def padded_matrix(xc, yc, values, step_x, step_y, normalize=False):
    xsteps = len(np.unique(xc))
    x_ls_raw = np.linspace(xc.min(), xc.max(), xsteps)
    x_ls_padded = np.linspace(xc.min() - step_x / 2, xc.max() + step_x / 2, xsteps + 1)
    ysteps = len(np.unique(yc))
    y_ls_raw = np.linspace(yc.min(), yc.max(), ysteps)
    y_ls_padded = np.linspace(yc.min() - step_y / 2, yc.max() + step_y / 2, ysteps + 1)
    X_raw, Y_raw = np.meshgrid(x_ls_raw, y_ls_raw)
    X_pad, Y_pad = np.meshgrid(x_ls_padded, y_ls_padded)
    V = griddata((xc, yc), values, (X_raw, Y_raw), method='nearest')
    if normalize:
        V = V / griddata((xc, yc), values, (0, 0), method='nearest')
    return X_pad, Y_pad, V


def unpadded_matrix(xc, yc, values, step_x, step_y, normalize=False):
    xsteps = len(np.unique(xc))
    x_ls_raw = np.linspace(xc.min(), xc.max(), xsteps)
    ysteps = len(np.unique(xc))
    y_ls_raw = np.linspace(yc.min(), yc.max(), ysteps)
    X_raw, Y_raw = np.meshgrid(x_ls_raw, y_ls_raw)
    V = griddata((xc, yc), values, (X_raw, Y_raw), method='nearest')
    if normalize:
        V = V / griddata((xc, yc), values, (0, 0), method='nearest')
    return X_raw, Y_raw, V


def prep_data(xydata, changing_axes=None, measure_step=None, interesting_mag='z', coord_in_steps=True,
              to_cm=1):
    """
    receives 6-column measured or simulated data and prep for further treatment.
    :param xydata: x, y, z, mag_x, mag_y, mag_z, xyz in steps or lengths.
    :param changing_axes: which two axes are changing.
    :param measure_step: step length. Required even if implied in data.
    :param interesting_mag: Which mag axis are you interested in.
    :param normalize: Normalize mag to center of dataset.
    :param coord_in_steps: Whether xyz coords are given in steps, in which case real xyz is derived by multiplying with
    step lengths.
    :return: (figure) x, y, x_step_length, y_step_length, mag (scalar).
    """
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
    try:
        xaxis = 'xyz'.index(changing_axes[0])
        yaxis = 'xyz'.index(changing_axes[1])
    except (IndexError, ValueError):
        raise ValueError('Invalid axes specifier: %s' % changing_axes)
    if coords[:, xaxis].min() == coords[:, xaxis].max():
        raise ValueError('provided figure x axis is constant across measured values.')
    if coords[:, yaxis].min() == coords[:, yaxis].max():
        raise ValueError('provided figure x axis is constant across measured values.')
    xstep = measure_step[xaxis]
    ystep = measure_step[yaxis]
    x_coords = coords[:, xaxis]
    y_coords = coords[:, yaxis]
    if coord_in_steps:
        x_coords *= xstep
        y_coords *= ystep
    else:
        x_coords *= to_cm
        y_coords *= to_cm
    return x_coords, y_coords, xstep, ystep, mags


def plot_intensity(data, axes=None, unit='nT', step_length=None, mag_axis='z', normalize=True, cis=True, to_cm=1,
                   vmin=None, vmax=None):
    x_coords, y_coords, xstep, ystep, mags = prep_data(data.copy(), changing_axes=axes, measure_step=step_length,
                                                       interesting_mag=mag_axis,
                                                       coord_in_steps=cis, to_cm=to_cm)

    X, Y, colors = padded_matrix(x_coords, y_coords, mags, xstep, ystep, normalize=normalize)
    f, ax = plt.subplots(1)
    ax.set_aspect(1)
    ax.set_xlabel('Distance from center/cm, %s axis' % axes[0])
    ax.set_ylabel('Distance from center/cm, %s axis' % axes[1])
    p = ax.pcolormesh(X, Y, colors, cmap='jet', vmin=vmin, vmax=vmax)
    cbar = f.colorbar(p)
    if normalize:
        cbar.ax.set_ylabel('Relative magnetic field strength')
    else:
        cbar.ax.set_ylabel('Magnetic field strength/%s' % unit)
    return f, ax


def plot_ortho_gradient(data, axes, step_length, mag_axis, cis=True, to_cm=1):
    x_coords, y_coords, xstep, ystep, mags = prep_data(data.copy(), changing_axes=axes, measure_step=step_length,
                                                       interesting_mag=mag_axis, coord_in_steps=cis,
                                                       to_cm=to_cm)
    X, Y, values = unpadded_matrix(x_coords, y_coords, mags, xstep, ystep, normalize=True)
    gradient = np.gradient(values, ystep, axis=0)
    f, ax = plt.subplots(1)
    ax.set_aspect(1)
    ax.set_xlabel('Distance from center/cm, %s axis' % axes[0])
    ax.set_ylabel('Distance from center/cm, %s axis' % axes[1])
    cs = ax.contour(X, Y, np.abs(gradient), [0.0002, 0.0005, 0.001, 0.002, 0.005], colors='w', zorder=10)
    csf = ax.contourf(X, Y, np.abs(gradient), 21, cmap='inferno')
    ax.clabel(cs, fontsize=11, inline=1, fmt='%.4f')

    cbar = f.colorbar(csf)
    cbar.ax.set_ylabel('FS grad. along vertical axis/cm')
    return f, ax


def plot_polar_gradient(data, step_length, mag_axis, radius, cis=True, to_cm=1):
    x_coords, y_coords, xstep, ystep, mags = prep_data(data.copy(), changing_axes='xy', measure_step=step_length,
                                                       interesting_mag=mag_axis, coord_in_steps=cis,
                                                       to_cm=to_cm)
    #TODO: Normalization now missing.
    x_coords = x_coords
    y_coords = y_coords
    t = np.linspace(0, np.pi * 2, 41)
    r = np.linspace(0, y_coords.max(), 41)
    r_step = y_coords.max() / 40
    T, R = np.meshgrid(t, r)
    XI = np.cos(T) * R
    YI = np.sin(T) * R
    MAG = griddata((x_coords, y_coords), mags, (XI, YI))
    f = plt.figure()
    ax = f.add_subplot(111, projection='polar')
    gradient = np.gradient(MAG, r_step, axis=1)
    cs = ax.contour(T, R, np.abs(gradient), [0.0005, 0.001, 0.002, 0.004], colors='w', zorder=10)
    csf = ax.pcolormesh(T, R, np.abs(gradient), cmap='inferno', vmax=0.002)
    cbar = f.colorbar(csf)
    ax.clabel(cs, fontsize=11, inline=1, fmt='%.4f')
    cbar.ax.set_ylabel('FS grad. along vertical axis/cm')


def draw_rectangle_cell(ax, width, height, x_offset=0, y_offset=0, color='w'):
    r = Rectangle([-width/2 + x_offset, -height/2 + y_offset], width, height,
                  fill=False, linewidth=1, edgecolor=color, linestyle='--')
    ax.plot(x_offset, y_offset, 'b+', color=color)
    ax.add_artist(r)
    return r


def draw_circular_cell(ax, diameter, color='w'):
    c = Circle([0, 0], diameter/2, fill=False, linewidth=1, edgecolor=color, linestyle='--')
    ax.plot(0, 0, 'b+', color=color)
    ax.add_artist(c)
    return c