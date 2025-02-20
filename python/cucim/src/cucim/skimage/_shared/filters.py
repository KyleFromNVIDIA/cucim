"""Filters used across multiple skimage submodules.

These are defined here to avoid circular imports.

The unit tests remain under skimage/filters/tests/
"""
from collections.abc import Iterable

import cupy as cp

import cucim.skimage._vendored.ndimage as ndi

from .._shared.utils import _supported_float_type, convert_to_float, warn


class _PatchClassRepr(type):
    """Control class representations in rendered signatures."""

    def __repr__(cls):
        return f"<{cls.__name__}>"


class ChannelAxisNotSet(metaclass=_PatchClassRepr):
    """Signal that the `channel_axis` parameter is not set.
    This is a proxy object, used to signal to `skimage.filters.gaussian` that
    the `channel_axis` parameter has not been set, in which case the function
    will determine whether a color channel is present. We cannot use ``None``
    for this purpose as it has its own meaning which indicates that the given
    image is grayscale.
    This automatic behavior was broken in v0.19, recovered but deprecated in
    v0.20 and will be removed in v0.21.
    """


def gaussian(
    image,
    sigma=1,
    output=None,
    mode="nearest",
    cval=0,
    preserve_range=False,
    truncate=4.0,
    *,
    channel_axis=ChannelAxisNotSet,
):
    """Multi-dimensional Gaussian filter.

    Parameters
    ----------
    image : array-like
        Input image (grayscale or color) to filter.
    sigma : scalar or sequence of scalars, optional
        Standard deviation for Gaussian kernel. The standard
        deviations of the Gaussian filter are given for each axis as a
        sequence, or as a single number, in which case it is equal for
        all axes.
    output : array, optional
        The ``output`` parameter passes an array in which to store the
        filter output.
    mode : {'reflect', 'constant', 'nearest', 'mirror', 'wrap'}, optional
        The ``mode`` parameter determines how the array borders are
        handled, where ``cval`` is the value when mode is equal to
        'constant'. Default is 'nearest'.
    cval : scalar, optional
        Value to fill past edges of input if ``mode`` is 'constant'. Default
        is 0.0
    preserve_range : bool, optional
        Whether to keep the original range of values. Otherwise, the input
        image is converted according to the conventions of ``img_as_float``.
        Also see
        https://scikit-image.org/docs/dev/user_guide/data_types.html
    truncate : float, optional
        Truncate the filter at this many standard deviations.
    channel_axis : int or None, optional
        If None, the image is assumed to be a grayscale (single channel) image.
        Otherwise, this parameter indicates which axis of the array corresponds
        to channels.

        .. warning::
            Automatic detection of the color channel based on the old deprecated
            ``multichannel=None`` was broken in version 0.19. In 0.20 this
            behavior is recovered. The last axis of an `image` with dimensions
            (M, N, 3) is interpreted as a color channel if `channel_axis` is
            not set. Starting with release 23.04.02, ``channel_axis=None`` will
            be used as the new default value.

    Returns
    -------
    filtered_image : ndarray
        the filtered array

    Notes
    -----
    This function is a wrapper around :func:`scipy.ndi.gaussian_filter`.

    Integer arrays are converted to float.

    The ``output`` should be floating point data type since gaussian converts
    to float provided ``image``. If ``output`` is not provided, another array
    will be allocated and returned as the result.

    The multi-dimensional filter is implemented as a sequence of
    one-dimensional convolution filters. The intermediate arrays are
    stored in the same data type as the output. Therefore, for output
    types with a limited precision, the results may be imprecise
    because intermediate results may be stored with insufficient
    precision.

    Examples
    --------

    >>> import cupy as cp
    >>> a = cp.zeros((3, 3))
    >>> a[1, 1] = 1
    >>> a
    array([[0., 0., 0.],
           [0., 1., 0.],
           [0., 0., 0.]])
    >>> gaussian(a, sigma=0.4)  # mild smoothing
    array([[0.00163116, 0.03712502, 0.00163116],
           [0.03712502, 0.84496158, 0.03712502],
           [0.00163116, 0.03712502, 0.00163116]])
    >>> gaussian(a, sigma=1)  # more smoothing
    array([[0.05855018, 0.09653293, 0.05855018],
           [0.09653293, 0.15915589, 0.09653293],
           [0.05855018, 0.09653293, 0.05855018]])
    >>> # Several modes are possible for handling boundaries
    >>> gaussian(a, sigma=1, mode='reflect')
    array([[0.08767308, 0.12075024, 0.08767308],
           [0.12075024, 0.16630671, 0.12075024],
           [0.08767308, 0.12075024, 0.08767308]])
    >>> # For RGB images, each is filtered separately
    >>> from skimage.data import astronaut
    >>> image = cp.array(astronaut())
    >>> filtered_img = gaussian(image, sigma=1, channel_axis=-1)

    """
    if channel_axis is ChannelAxisNotSet:
        if image.ndim == 3 and image.shape[-1] == 3:
            warn(
                "Automatic detection of the color channel was deprecated in "
                "v0.19, and `channel_axis=None` will be the new default in "
                "v0.21. Set `channel_axis=-1` explicitly to silence this "
                "warning.",
                FutureWarning,
                stacklevel=2,
            )
            channel_axis = -1
        else:
            channel_axis = None

    # CuPy Backend: refactor to avoid overhead of cp.any(cp.asarray(sigma))
    sigma_msg = "Sigma values less than zero are not valid"
    if not isinstance(sigma, Iterable):
        if sigma < 0:
            raise ValueError(sigma_msg)
    elif any(s < 0 for s in sigma):
        raise ValueError(sigma_msg)

    if channel_axis is not None:
        # do not filter across channels
        if not isinstance(sigma, Iterable):
            sigma = [sigma] * (image.ndim - 1)
        if len(sigma) == image.ndim - 1:
            sigma = list(sigma)
            sigma.insert(channel_axis % image.ndim, 0)
    image = convert_to_float(image, preserve_range)
    float_dtype = _supported_float_type(image.dtype)
    image = image.astype(float_dtype, copy=False)
    if output is None:
        output = cp.empty_like(image)
    elif not cp.issubdtype(output.dtype, cp.floating):
        raise ValueError("Provided output data type is not float")
    ndi.gaussian_filter(
        image, sigma, output=output, mode=mode, cval=cval, truncate=truncate
    )
    return output
