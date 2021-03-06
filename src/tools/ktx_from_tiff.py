#!/bin/env python

"""
Copyright (c) 2016 Christopher M. Bruns

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

# built-in python modules
import sys
import io
import time
from glob import glob
import os
import math
import datetime

# third party python modules
from OpenGL import GL
from tifffile import TiffFile
import tifffile
import numpy

# local python modules
import ktx
from ktx.util import create_mipmaps, mipmap_dimension, interleave_channel_arrays, downsample_array_xy

"""
TODO: For converting rendered octree blocks, include the following precomputed:
  * all mipmap levels
  * optional intensity downsampling, with affine reestimation parameters
  * optional spatial downsampling
  * other metadata:
      * distance units e.g. "micrometers", for all the transforms below
      * transform from texture coordinates to Cartesian reference space
      * Optional transform from texture coordinates to Allen reference space
      * center xyz in reference space
      * bounding radius
      * nominal spatial resolution range at this level
      * specimen ID, e.g. "2015-06-19-johan-full"
      * parent tile/block ID, e.g. "/1/5/4/8/default.[0,1].tif"
      * relation to parent tile/block, e.g. "downsampled 2X in XY; rescaled intensity to 8 bits; sub-block (1,2) of (6,6)
      * multiscale level ID (int)
          * of total multiscale level count (int)
      * per channel
          * affine parameters to approximate background level of first channel, for dynamic unmixing
          * min, max, average, median intensities
          * proportion of zero/NaN in this block
      * creation time
      * name of program used to create this block
      * version of program used to create this block
      * texture coordinate bounds for display (because there might be padding...)
"""

def test_downsample_xy(filter_='arthur'):
    fname = "E:/brunsc/projects/ktxtiff/octree_tip/default.0.tif"
    with TiffFile(fname) as tif:
        data = tif.asarray()
    t0 = time.time()
    downsampled = downsample_array_xy(data, filter_=filter_)
    t1 = time.time()
    print (t1-t0, " seconds elapsed time to downsample volume in XY")
    tifffile.imsave("downsampled.tif", downsampled)
    t2 = time.time()
    print (t2-t1, " seconds elapsed time to save downsampled volume in tiff format to disk")
def test_interleave_channel_arrays():
    a = numpy.array( (1,2,3,4,5,), dtype='uint16' )
    b = numpy.array( (6,7,8,9,10,), dtype='uint16' )
    # print (a)
    # print (b)
    c = interleave_channel_arrays( (a,b,) )
    # print (c)
    assert numpy.array_equal(c, numpy.array(
        [[ 1,  6],
         [ 2,  7],
         [ 3,  8],
         [ 4,  9],
         [ 5, 10]]))

def test_create_mipmaps(filter_='arthur'):
    fname = "E:/brunsc/projects/ktxtiff/octree_tip/default.0.tif"
    with TiffFile(fname) as tif:
        data = tif.asarray()
    data = downsample_array_xy(data, filter_=filter_)
    t0 = time.time()
    mipmaps = create_mipmaps(data, filter_=filter_)
    t1 = time.time()
    print (t1-t0, " seconds elapsed time to compute mipmaps")
    for i in range(len(mipmaps)):
        tifffile.imsave("test_mipmap%02d.tif" % i, mipmaps[i])
    t2 = time.time()
    print (t2-t1, " seconds elapsed time to save mipmaps in tiff format to disk")

def test_create_tiff():
    # https://pypi.python.org/pypi/tifffile
    fname = "E:/brunsc/projects/ktxtiff/octree_tip/default.0.tif"
    with TiffFile(fname) as tif:
        data1 = tif.asarray()
        # tifffile.imsave('test1.tif', data1)
    fname = "E:/brunsc/projects/ktxtiff/octree_tip/default.1.tif"
    with TiffFile(fname) as tif:
        data2 = tif.asarray()
        # tifffile.imsave('test2.tif', data2)
    # TODO unmixing test
    # compute channel 1/2 unmixing parameters
    # For lower end of mapping, just use lower quartile intensity (non-zero!)
    lower1 = numpy.percentile(data1[data1 != 0], 40)
    lower2 = numpy.percentile(data2[data2 != 0], 40)
    print (lower1, lower2)
    # For upper end of mapping, use voxels that are bright in BOTH channels
    m_a = numpy.median(data1[data1 != 0])
    m_b = numpy.median(data2[data2 != 0])
    s_a = numpy.std(data1[data1 != 0])
    s_b = numpy.std(data2[data2 != 0])
    upper1 = numpy.median(data1[(data1 > m_a + 2*s_a) & (data2 > m_b + 2*s_b)])
    upper2 = numpy.median(data2[(data1 > m_a + 2*s_a) & (data2 > m_b + 2*s_b)])
    print (upper1, upper2)
    # transform data2 to match data1
    scale = (upper1 - lower1) / (upper2 - lower2)
    offset = upper1 - upper2 * scale
    scale2 = (upper2 - lower2) / (upper1 - lower1)
    offset2 = upper2 - upper1 * scale2
    data2b = numpy.array(data2, dtype='float32')
    data2b *= scale
    data2b += offset
    data2b[data2 == 0] = 0
    data2b[data2b <= 0] = 0
    data2b = numpy.array(data2b, dtype=data1.dtype)
    # TODO ktx to tiff
    # Needs 1 or 3 channels for Fiji to load it OK
    # data3 = numpy.zeros_like(data1)
    tissue = numpy.minimum(data1, data2)
    tissue_base = numpy.percentile(tissue[tissue != 0], 4) - 1
    tissue = numpy.array(tissue, dtype='float32') # so we can handle negative numbers
    print (tissue_base)
    tissue -= tissue_base
    tissue[tissue <= 0] = 0
    tissue = numpy.array(tissue, dtype=data1.dtype)
    #
    unmixed1 = numpy.array(data1, dtype='float32')
    unmixed1 -= data2b
    # unmixed1 += s_a # tweak background up to show more stuff
    unmixed1[unmixed1 <= 0] = 0
    unmixed1 = numpy.array(unmixed1, dtype=data1.dtype)
    #
    data1b = numpy.array(data1, dtype='float32')
    data1b *= scale2
    data1b += offset2
    data1b[data1 == 0] = 0
    data1b[data1b <= 0] = 0
    data1b = numpy.array(data1b, dtype=data1.dtype)
    unmixed2 = numpy.array(data2, dtype='float32')
    unmixed2 -= data1b
    # unmixed2 += s_b # tweak background up to show more stuff
    unmixed2[unmixed2 <= 0] = 0
    unmixed2 = numpy.array(unmixed2, dtype=data1.dtype)
    #
    print (tissue.shape)
    data123 = interleave_channel_arrays( (data2, data1b, unmixed2) )
    # print (data123.shape)
    tifffile.imsave('test123.tif', data123)

def ktx_from_mouselight_octree_folder(input_folder_name,
                              output_folder_name,
                              num_levels=1, # '0' means 'all'
                              mipmap_filter='max', 
                              downsample_xy=True, 
                              downsample_intensity=False):
    # Parse geometry data from top level transform.txt
    metadata = dict()
    with io.open(os.path.join(input_folder_name, "transform.txt"), 'r') as transform_file:
        for line in transform_file:
            fields = line.split(": ")
            if len(fields) != 2:
                continue
            metadata[fields[0].strip()] = fields[1].strip()
    # Get original tiff file dimensions, to help compute geometry correctly
    with tifffile.TiffFile(os.path.join(input_folder_name, "default.0.tif")) as tif:
        original_tiff_dimensions = tif.asarray().shape
    # for k, v in metadata.items():
    #     print (k, v)
    if num_levels == 0:
        num_levels = int(metadata["nl"])
    assert num_levels > 0
    folder = input_folder_name
    for level in range(num_levels):
        tiffs = glob(os.path.join(folder, "default.*.tif"))
        ktx_obj = ktx_from_tiff_channel_files(tiffs, mipmap_filter, downsample_xy, downsample_intensity)
        # Populate custom block metadata
        kh = ktx_obj.header
        # kv = ktx_obj.header.key_value_metadata
        # kv[b'distance_units'] = b'micrometers'
        kh["distance_units"] = "micrometers"
        umFromNm = 1.0/1000.0
        # Origin of volume (corner of corner voxel)
        ox = umFromNm*float(metadata['ox'])
        oy = umFromNm*float(metadata['oy'])
        oz = umFromNm*float(metadata['oz'])
        # Size of entire volume
        # Use original dimensions, to account for downsampling...
        sx = umFromNm * original_tiff_dimensions[2] * float(metadata['sx']) 
        sy = umFromNm * original_tiff_dimensions[1] * float(metadata['sy'])
        sz = umFromNm * original_tiff_dimensions[0] * float(metadata['sz'])
        xform = numpy.array([
                [sx, 0, 0, ox],
                [0, sy, 0, oy],
                [0, 0, sz, oz],
                [0, 0, 0, 1],], dtype='float32')
        # print(xform)
        kh["xyz_from_texcoord_xform"] = xform
        # print (kh["xyz_from_texcoord_xform"])
        #
        center = numpy.array( (ox + 0.5*sx, oy + 0.5*sy, oz + 0.5*sz,), )
        radius = math.sqrt(sx*sx + sy*sy + sz*sz)/16.0
        kh['bounding_sphere_center'] = center
        kh['bounding_sphere_radius'] = radius
        # Nominal resolution
        resX = sx / ktx_obj.header.pixel_width
        resY = sy / ktx_obj.header.pixel_height
        resZ = sz / ktx_obj.header.pixel_depth
        rms = math.sqrt(numpy.mean(numpy.square([resX, resY, resZ],)))
        kh['nominal_resolution'] = rms
        # print (kh['nominal_resolution'])
        # Specimen ID
        kh['specimen_id'] = os.path.split(input_folder_name)[-1]
        # print (kh['specimen_id'])
        # TODO: octree block ID
        # Relation to parent tile/block
        kh['mipmap_filter'] = mipmap_filter
        relations = list()
        if downsample_xy:
            relations.append("downsampled 2X in X & Y")
        if downsample_intensity:
            relations.append("rescaled intensity to 8 bits")
        if len(relations) == 0:
            relations.append("unchanged")
        kh['relation_to_parent'] = ";".join(relations)
        # print (kh['relation_to_parent'])
        kh['multiscale_level_id'] = level
        kh['multiscale_total_levels'] = metadata['nl']
        # TODO: Per channel statistics
        kh['ktx_file_creation_date'] = datetime.datetime.now()
        # print (kh['ktx_file_creation_date'])
        import __main__ #@UnresolvedImport
        kh['ktx_file_creation_program'] = __main__.__file__
        # print (kh['ktx_file_creation_program'])
        kh['pyktx_version'] = ktx.__version__
        # print (kh['ktx_package_version'])
        # TODO: Texture coordinate bounds for display
        # Write LZ4-compressed KTX file
        t1 = time.time()
        with io.open('test.ktx', 'wb') as ktx_out:
            temp = io.BytesIO()
            ktx_obj.write_stream(temp)
            ktx_out.write(temp.getvalue())        # Create tiff file for sanity check testing
        t2 = time.time()
        print ("Creating uncompressed ktx file took %.3f seconds" % (t2 - t1))
        # TODO: create tiffFromKtx.py as a separate tool
        # tifffile.imsave('test.tif', ktx_obj.asarray(0))

def ktx_from_tiff_channel_files(channel_tiff_names, mipmap_filter='max', downsample_xy=True, downsample_intensity=False):
    """
    Load multiple single-channel tiff files, and create a multichannel Ktx object.
    """
    t0 = time.time()
    channels = list()
    for fname in channel_tiff_names:
        with TiffFile(fname) as tif:
            arr = tif.asarray()
            if downsample_xy:
                arr = downsample_array_xy(arr, mipmap_filter)
            channels.append(arr)
    t1 = time.time()
    print ("loading tiff files took %.3f seconds" % (t1 - t0))
    if downsample_intensity:
        new_channels = list()
        channel_transforms = list()
        for channel in channels:
            min_ = numpy.min(channel[channel != 0])
            max_ = numpy.max(channel[channel != 0])
            scale = 1.0
            offset = min_ - 1
            if max_ - min_ > 255: # need a lossy contraction of intensities
                # Discard dimmest 2% of intensities
                min_ = numpy.percentile(channel[channel != 0], 2)
                median = numpy.median(channel[channel != 0])
                max_ = numpy.max(channel[channel != 0])
                # Discard intensities above 90% of max
                max_ = median + 0.90 * (max_ - median)
                print(min_, median, max_)
                scale = (max_ - min_) / 255.0
                offset = min_ - 1
            if channel.dtype.itemsize == 2:
                c = numpy.array(channel, dtype='float32')
                c -= offset
                c /= scale
                c[c<0] = 0
                if channel.dtype == numpy.uint16:
                    dt = numpy.uint8
                else:
                    raise # TODO: more cases
                c = numpy.array(c, dtype=dt)
                new_channels.append(c)
                channel_transforms.append( tuple([scale, offset]) )
            else:
                raise # TODO:
        channels = new_channels
    combined = interleave_channel_arrays(channels)
    ktx_obj = ktx.Ktx.from_ndarray(combined, mipmap_filter=mipmap_filter)
    # Include metadata for reconstructing original intensities
    if downsample_intensity:
        c = 0
        for ct in channel_transforms:
            ktx_obj.header['intensity_transform_%d'%c] = ct
            c += 1
    t2 = time.time()
    print ("creating swizzled mipmapped ktx data took %.3f seconds" % (t2 - t1))    
    return ktx_obj

def main():
    test_mipmap_dimension()
    test_downsample_xy()
    return
    "Interleave multiple single channel tiff files into a multi-channel KTX file"
    arrays = list()
    for arg in sys.argv[1:]:
        for fname in glob(arg):
            print (fname)
            with TiffFile(fname) as tif:
                print (len(tif.pages))
                data = tif.asarray()
                print (data.shape)
                arrays.append(data)
                # print (numpy.percentile(data[data != 0], [25, 99]))
    a = arrays[0]
    b = arrays[1]
    # TODO: generate linear unmixing parameters appropriate for both dim and bright sections
    # Use only non-zero locations for basic statistics
    m_a = numpy.median(a[a != 0])
    s_a = numpy.std(a[a != 0])
    m_b = numpy.median(b[b != 0])
    s_b = numpy.std(b[b != 0])
    # Statistic for locations where both channels are bright at the same location
    h_a = numpy.median(a[(a > m_a + 2*s_a) & (b > m_b + 2*s_b)])
    print (m_a, s_a, h_a)
    h_b = numpy.median(b[(a > m_a + 2*s_a) & (b > m_b + 2*s_b)])
    print (m_b, s_b, h_b)
    # Interleave two channels
    # http://stackoverflow.com/questions/5347065/interweaving-two-numpy-arrays
    c = numpy.empty( shape=(a.shape[0], a.shape[1], a.shape[2], len(arrays)), dtype=a.dtype)
    for i in range(len(arrays)):
        c[:,:,:,i] = arrays[i]
    print (c.shape)
    dt = c.dtype
    ktx_obj = ktx.Ktx()
    kh = ktx_obj.header
    if dt.byteorder == '<':
        kh.little_endian = True
    elif dt.byteorder == '=':
        kh.little_endian = sys.byteorder == 'little'
    else:
        raise # TODO
    print (dt.byteorder)
    print (kh.little_endian)
    if dt.kind == 'u':
        if dt.itemsize == 2:
            kh.gl_type = GL.GL_UNSIGNED_SHORT
        elif dt.itemsize == 1:
            kh.gl_type = GL.GL_UNSIGNED_BYTE
        else:
            raise # TODO
    else:
        raise # TODO
    #
    kh.gl_type_size = dt.itemsize
    #
    if c.shape[3] == 1:
        kh.gl_format = kh.gl_base_internal_format = GL.GL_RED
    elif c.shape[3] == 2:
        kh.gl_format = kh.gl_base_internal_format = GL.GL_RG
    elif c.shape[3] == 3:
        kh.gl_format = kh.gl_base_internal_format = GL.GL_RGB
    elif c.shape[3] == 4:
        kh.gl_format = kh.gl_base_internal_format = GL.GL_RGBA
    else:
        raise # TODO
    #
    if kh.gl_base_internal_format == GL.GL_RG and kh.gl_type == GL.GL_UNSIGNED_SHORT:
        kh.gl_internal_format = GL.GL_RG16UI
    else:
        raise # TODO
    #
    kh.pixel_width = c.shape[2]
    kh.pixel_height = c.shape[1]
    kh.pixel_depth = c.shape[0]
    kh.number_of_array_elements = 0
    kh.number_of_faces = 0
    kh.number_of_mipmap_levels = 1 # TODO zero for autogenerate?
    # TODO - key/value pairs for provenance
    ktx_obj.image_data.mipmaps.clear()
    ktx_obj.image_data.mipmaps.append(c.tostring())
    
if __name__ == "__main__":
    """
    ktx_from_tiff_channel_files(
            ("E:/brunsc/projects/ktxtiff/octree_tip/default.1.tif",
            "E:/brunsc/projects/ktxtiff/octree_tip/default.0.tif",
            ), )
    """
    """
    ktx_from_mouselight_octree_folder(
            input_folder_name='//fxt/nobackup2/mouselight/2015-06-19-johan-full', 
            output_folder_name='',
            mipmap_filter='arthur', 
            downsample_xy=True,
            downsample_intensity=True)
    """
    test_create_mipmaps('arthur')
