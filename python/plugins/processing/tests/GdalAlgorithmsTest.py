# -*- coding: utf-8 -*-

"""
***************************************************************************
    GdalAlgorithmTests.py
    ---------------------
    Date                 : January 2016
    Copyright            : (C) 2016 by Matthias Kuhn
    Email                : matthias@opengis.ch
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

__author__ = 'Matthias Kuhn'
__date__ = 'January 2016'
__copyright__ = '(C) 2016, Matthias Kuhn'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = ':%H$'

import AlgorithmsTestBase
from processing.algs.gdal.OgrToPostGis import OgrToPostGis
from processing.algs.gdal.GdalUtils import GdalUtils
from processing.algs.gdal.ClipRasterByExtent import ClipRasterByExtent
from processing.algs.gdal.ClipRasterByMask import ClipRasterByMask
from processing.algs.gdal.gdal2tiles import gdal2tiles
from processing.algs.gdal.contour import contour
from processing.algs.gdal.GridAverage import GridAverage
from processing.algs.gdal.GridDataMetrics import GridDataMetrics
from processing.algs.gdal.GridInverseDistance import GridInverseDistance
from processing.algs.gdal.GridInverseDistanceNearestNeighbor import GridInverseDistanceNearestNeighbor
from processing.algs.gdal.GridLinear import GridLinear
from processing.algs.gdal.GridNearestNeighbor import GridNearestNeighbor
from processing.algs.gdal.proximity import proximity
from processing.algs.gdal.rasterize import rasterize
from processing.algs.gdal.translate import translate
from processing.algs.gdal.warp import warp

from qgis.core import (QgsProcessingContext,
                       QgsProcessingFeedback,
                       QgsApplication,
                       QgsVectorLayer,
                       QgsFeature,
                       QgsGeometry,
                       QgsPointXY,
                       QgsProject,
                       QgsRectangle,
                       QgsProcessingException,
                       QgsProcessingFeatureSourceDefinition)
import nose2
import os
import shutil
import tempfile

from qgis.testing import (
    start_app,
    unittest
)

testDataPath = os.path.join(os.path.dirname(__file__), 'testdata')


class TestGdalAlgorithms(unittest.TestCase, AlgorithmsTestBase.AlgorithmsTest):

    @classmethod
    def setUpClass(cls):
        start_app()
        from processing.core.Processing import Processing
        Processing.initialize()
        cls.cleanup_paths = []

    @classmethod
    def tearDownClass(cls):
        for path in cls.cleanup_paths:
            shutil.rmtree(path)

    def test_definition_file(self):
        return 'gdal_algorithm_tests.yaml'

    def testCommandName(self):
        # Test that algorithms report a valid commandName
        p = QgsApplication.processingRegistry().providerById('gdal')
        for a in p.algorithms():
            self.assertTrue(a.commandName(), 'Algorithm {} has no commandName!'.format(a.id()))

    def testNoParameters(self):
        # Test that algorithms throw QgsProcessingExceptions and not base Python
        # exceptions when no parameters specified
        p = QgsApplication.processingRegistry().providerById('gdal')
        context = QgsProcessingContext()
        feedback = QgsProcessingFeedback()
        for a in p.algorithms():
            try:
                a.getConsoleCommands({}, context, feedback)
            except QgsProcessingException:
                pass

    def testGetOgrCompatibleSourceFromMemoryLayer(self):
        # create a memory layer and add to project and context
        layer = QgsVectorLayer("Point?field=fldtxt:string&field=fldint:integer",
                               "testmem", "memory")
        self.assertTrue(layer.isValid())
        pr = layer.dataProvider()
        f = QgsFeature()
        f.setAttributes(["test", 123])
        f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(100, 200)))
        f2 = QgsFeature()
        f2.setAttributes(["test2", 457])
        f2.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(100, 200)))
        self.assertTrue(pr.addFeatures([f, f2]))
        self.assertEqual(layer.featureCount(), 2)
        QgsProject.instance().addMapLayer(layer)
        context = QgsProcessingContext()
        context.setProject(QgsProject.instance())

        alg = QgsApplication.processingRegistry().createAlgorithmById('gdal:buffervectors')
        self.assertIsNotNone(alg)
        parameters = {'INPUT': 'testmem'}
        feedback = QgsProcessingFeedback()
        # check that memory layer is automatically saved out to shape when required by GDAL algorithms
        ogr_data_path, ogr_layer_name = alg.getOgrCompatibleSource('INPUT', parameters, context, feedback,
                                                                   executing=True)
        self.assertTrue(ogr_data_path)
        self.assertTrue(ogr_data_path.endswith('.shp'))
        self.assertTrue(os.path.exists(ogr_data_path))
        self.assertTrue(ogr_layer_name)

        # make sure that layer has correct features
        res = QgsVectorLayer(ogr_data_path, 'res')
        self.assertTrue(res.isValid())
        self.assertEqual(res.featureCount(), 2)

        QgsProject.instance().removeMapLayer(layer)

    def testGetOgrCompatibleSourceFromFeatureSource(self):
        # create a memory layer and add to project and context
        layer = QgsVectorLayer("Point?field=fldtxt:string&field=fldint:integer",
                               "testmem", "memory")
        self.assertTrue(layer.isValid())
        pr = layer.dataProvider()
        f = QgsFeature()
        f.setAttributes(["test", 123])
        f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(100, 200)))
        f2 = QgsFeature()
        f2.setAttributes(["test2", 457])
        f2.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(100, 200)))
        self.assertTrue(pr.addFeatures([f, f2]))
        self.assertEqual(layer.featureCount(), 2)
        # select first feature
        layer.selectByIds([next(layer.getFeatures()).id()])
        self.assertEqual(len(layer.selectedFeatureIds()), 1)
        QgsProject.instance().addMapLayer(layer)
        context = QgsProcessingContext()
        context.setProject(QgsProject.instance())

        alg = QgsApplication.processingRegistry().createAlgorithmById('gdal:buffervectors')
        self.assertIsNotNone(alg)
        parameters = {'INPUT': QgsProcessingFeatureSourceDefinition('testmem', True)}
        feedback = QgsProcessingFeedback()
        # check that memory layer is automatically saved out to shape when required by GDAL algorithms
        ogr_data_path, ogr_layer_name = alg.getOgrCompatibleSource('INPUT', parameters, context, feedback,
                                                                   executing=True)
        self.assertTrue(ogr_data_path)
        self.assertTrue(ogr_data_path.endswith('.shp'))
        self.assertTrue(os.path.exists(ogr_data_path))
        self.assertTrue(ogr_layer_name)

        # make sure that layer has only selected feature
        res = QgsVectorLayer(ogr_data_path, 'res')
        self.assertTrue(res.isValid())
        self.assertEqual(res.featureCount(), 1)

        QgsProject.instance().removeMapLayer(layer)

    def testOgrLayerNameExtraction(self):
        outdir = tempfile.mkdtemp()
        self.cleanup_paths.append(outdir)

        def _copyFile(dst):
            shutil.copyfile(os.path.join(testDataPath, 'custom', 'grass7', 'weighted.csv'), dst)

        # OGR provider - single layer
        _copyFile(os.path.join(outdir, 'a.csv'))
        name = GdalUtils.ogrLayerName(outdir)
        self.assertEqual(name, 'a')

        # OGR provider - multiple layers
        _copyFile(os.path.join(outdir, 'b.csv'))
        name1 = GdalUtils.ogrLayerName(outdir + '|layerid=0')
        name2 = GdalUtils.ogrLayerName(outdir + '|layerid=1')
        self.assertEqual(sorted([name1, name2]), ['a', 'b'])

        name = GdalUtils.ogrLayerName(outdir + '|layerid=2')
        self.assertIsNone(name)

        # OGR provider - layername takes precedence
        name = GdalUtils.ogrLayerName(outdir + '|layername=f')
        self.assertEqual(name, 'f')

        name = GdalUtils.ogrLayerName(outdir + '|layerid=0|layername=f')
        self.assertEqual(name, 'f')

        name = GdalUtils.ogrLayerName(outdir + '|layername=f|layerid=0')
        self.assertEqual(name, 'f')

        # SQLiite provider
        name = GdalUtils.ogrLayerName('dbname=\'/tmp/x.sqlite\' table="t" (geometry) sql=')
        self.assertEqual(name, 't')

        # PostgreSQL provider
        name = GdalUtils.ogrLayerName(
            'port=5493 sslmode=disable key=\'edge_id\' srid=0 type=LineString table="city_data"."edge" (geom) sql=')
        self.assertEqual(name, 'city_data.edge')

    def testOgrConnectionStringAndFormat(self):
        context = QgsProcessingContext()
        output, outputFormat = GdalUtils.ogrConnectionStringAndFormat('d:/test/test.shp', context)
        self.assertEqual(output, '"d:/test/test.shp"')
        self.assertEqual(outputFormat, '"ESRI Shapefile"')
        output, outputFormat = GdalUtils.ogrConnectionStringAndFormat('d:/test/test.mif', context)
        self.assertEqual(output, '"d:/test/test.mif"')
        self.assertEqual(outputFormat, '"MapInfo File"')

    def testGdalTranslate(self):
        context = QgsProcessingContext()
        feedback = QgsProcessingFeedback()
        source = os.path.join(testDataPath, 'dem.tif')
        translate_alg = translate()
        translate_alg.initAlgorithm()

        # with no NODATA value
        self.assertEqual(
            translate_alg.getConsoleCommands({'INPUT': source,
                                              'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_translate',
             '-ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])
        # with NODATA value
        self.assertEqual(
            translate_alg.getConsoleCommands({'INPUT': source,
                                              'NODATA': 9999,
                                              'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_translate',
             '-a_nodata 9999.0 ' +
             '-ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])
        # with "0" NODATA value
        self.assertEqual(
            translate_alg.getConsoleCommands({'INPUT': source,
                                              'NODATA': 0,
                                              'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_translate',
             '-a_nodata 0.0 ' +
             '-ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])
        # with target srs
        self.assertEqual(
            translate_alg.getConsoleCommands({'INPUT': source,
                                              'TARGET_CRS': 'EPSG:3111',
                                              'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_translate',
             '-a_srs EPSG:3111 ' +
             '-ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])
        # with target srs
        self.assertEqual(
            translate_alg.getConsoleCommands({'INPUT': source,
                                              'TARGET_CRS': 'EPSG:3111',
                                              'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_translate',
             '-a_srs EPSG:3111 ' +
             '-ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])
        # with copy subdatasets
        self.assertEqual(
            translate_alg.getConsoleCommands({'INPUT': source,
                                              'COPY_SUBDATASETS': True,
                                              'OUTPUT': 'd:/temp/check.tif'}, context, feedback),
            ['gdal_translate',
             '-sds ' +
             '-ot Float32 -of GTiff ' +
             source + ' ' +
             'd:/temp/check.tif'])

    def testClipRasterByExtent(self):
        context = QgsProcessingContext()
        feedback = QgsProcessingFeedback()
        source = os.path.join(testDataPath, 'dem.tif')
        alg = ClipRasterByExtent()
        alg.initAlgorithm()
        extent = QgsRectangle(1, 2, 3, 4)

        # with no NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'EXTENT': extent,
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_translate',
             '-projwin 0.0 0.0 0.0 0.0 -ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])
        # with NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'EXTENT': extent,
                                    'NODATA': 9999,
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_translate',
             '-projwin 0.0 0.0 0.0 0.0 -a_nodata 9999.0 -ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])
        # with "0" NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'EXTENT': extent,
                                    'NODATA': 0,
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_translate',
             '-projwin 0.0 0.0 0.0 0.0 -a_nodata 0.0 -ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])

    def testClipRasterByMask(self):
        context = QgsProcessingContext()
        feedback = QgsProcessingFeedback()
        source = os.path.join(testDataPath, 'dem.tif')
        mask = os.path.join(testDataPath, 'polys.gml')
        alg = ClipRasterByMask()
        alg.initAlgorithm()

        # with no NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'MASK': mask,
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdalwarp',
             '-ot Float32 -of JPEG -cutline ' +
             mask + ' -crop_to_cutline ' + source + ' ' +
             'd:/temp/check.jpg'])
        # with NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'MASK': mask,
                                    'NODATA': 9999,
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdalwarp',
             '-ot Float32 -of JPEG -cutline ' +
             mask + ' -crop_to_cutline -dstnodata 9999.0 ' + source + ' ' +
             'd:/temp/check.jpg'])
        # with "0" NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'MASK': mask,
                                    'NODATA': 0,
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdalwarp',
             '-ot Float32 -of JPEG -cutline ' +
             mask + ' -crop_to_cutline -dstnodata 0.0 ' + source + ' ' +
             'd:/temp/check.jpg'])

    def testContour(self):
        context = QgsProcessingContext()
        feedback = QgsProcessingFeedback()
        source = os.path.join(testDataPath, 'dem.tif')
        alg = contour()
        alg.initAlgorithm()

        # with no NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'BAND': 1,
                                    'FIELD_NAME': 'elev',
                                    'INTERVAL': 5,
                                    'OUTPUT': 'd:/temp/check.shp'}, context, feedback),
            ['gdal_contour',
             '-b 1 -a elev -i 5.0 -f "ESRI Shapefile" ' +
             source + ' ' +
             '"d:/temp/check.shp"'])
        # with NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'BAND': 1,
                                    'FIELD_NAME': 'elev',
                                    'INTERVAL': 5,
                                    'NODATA': 9999,
                                    'OUTPUT': 'd:/temp/check.shp'}, context, feedback),
            ['gdal_contour',
             '-b 1 -a elev -i 5.0 -snodata 9999.0 -f "ESRI Shapefile" ' +
             source + ' ' +
             '"d:/temp/check.shp"'])
        # with "0" NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'BAND': 1,
                                    'FIELD_NAME': 'elev',
                                    'INTERVAL': 5,
                                    'NODATA': 0,
                                    'OUTPUT': 'd:/temp/check.gpkg'}, context, feedback),
            ['gdal_contour',
             '-b 1 -a elev -i 5.0 -snodata 0.0 -f "GPKG" ' +
             source + ' ' +
             '"d:/temp/check.gpkg"'])

    def testGdal2Tiles(self):
        context = QgsProcessingContext()
        feedback = QgsProcessingFeedback()
        source = os.path.join(testDataPath, 'dem.tif')
        alg = gdal2tiles()
        alg.initAlgorithm()

        # with no NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'OUTPUT': 'd:/temp/'}, context, feedback),
            ['gdal2tiles.py',
             '-p mercator -w all -r average ' +
             source + ' ' +
             'd:/temp/'])
        # with NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'NODATA': -9999,
                                    'OUTPUT': 'd:/temp/'}, context, feedback),
            ['gdal2tiles.py',
             '-p mercator -w all -r average -a -9999.0 ' +
             source + ' ' +
             'd:/temp/'])
        # with "0" NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'NODATA': 0,
                                    'OUTPUT': 'd:/temp/'}, context, feedback),
            ['gdal2tiles.py',
             '-p mercator -w all -r average -a 0.0 ' +
             source + ' ' +
             'd:/temp/'])

    def testGridAverage(self):
        context = QgsProcessingContext()
        feedback = QgsProcessingFeedback()
        source = os.path.join(testDataPath, 'points.gml')
        alg = GridAverage()
        alg.initAlgorithm()

        # with no NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_grid',
             '-l points -a average:radius1=0.0:radius2=0.0:angle=0.0:min_points=0:nodata=0.0 -ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])
        # with NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'NODATA': 9999,
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_grid',
             '-l points -a average:radius1=0.0:radius2=0.0:angle=0.0:min_points=0:nodata=9999.0 -ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])
        # with "0" NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'NODATA': 0,
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_grid',
             '-l points -a average:radius1=0.0:radius2=0.0:angle=0.0:min_points=0:nodata=0.0 -ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])

    def testGridDataMetrics(self):
        context = QgsProcessingContext()
        feedback = QgsProcessingFeedback()
        source = os.path.join(testDataPath, 'points.gml')
        alg = GridDataMetrics()
        alg.initAlgorithm()

        # with no NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_grid',
             '-l points -a minimum:radius1=0.0:radius2=0.0:angle=0.0:min_points=0:nodata=0.0 -ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])
        # with NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'NODATA': 9999,
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_grid',
             '-l points -a minimum:radius1=0.0:radius2=0.0:angle=0.0:min_points=0:nodata=9999.0 -ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])
        # with "0" NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'NODATA': 0,
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_grid',
             '-l points -a minimum:radius1=0.0:radius2=0.0:angle=0.0:min_points=0:nodata=0.0 -ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])

    def testGridInverseDistance(self):
        context = QgsProcessingContext()
        feedback = QgsProcessingFeedback()
        source = os.path.join(testDataPath, 'points.gml')
        alg = GridInverseDistance()
        alg.initAlgorithm()

        # with no NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_grid',
             '-l points -a invdist:power=2.0:smothing=0.0:radius1=0.0:radius2=0.0:angle=0.0:max_points=0:min_points=0:nodata=0.0 -ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])
        # with NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'NODATA': 9999,
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_grid',
             '-l points -a invdist:power=2.0:smothing=0.0:radius1=0.0:radius2=0.0:angle=0.0:max_points=0:min_points=0:nodata=9999.0 -ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])
        # with "0" NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'NODATA': 0,
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_grid',
             '-l points -a invdist:power=2.0:smothing=0.0:radius1=0.0:radius2=0.0:angle=0.0:max_points=0:min_points=0:nodata=0.0 -ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])

    def testGridInverseDistanceNearestNeighbour(self):
        context = QgsProcessingContext()
        feedback = QgsProcessingFeedback()
        source = os.path.join(testDataPath, 'points.gml')
        alg = GridInverseDistanceNearestNeighbor()
        alg.initAlgorithm()

        # with no NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_grid',
             '-l points -a invdistnn:power=2.0:smothing=0.0:radius=1.0:max_points=12:min_points=0:nodata=0.0 -ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])
        # with NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'NODATA': 9999,
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_grid',
             '-l points -a invdistnn:power=2.0:smothing=0.0:radius=1.0:max_points=12:min_points=0:nodata=9999.0 -ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])
        # with "0" NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'NODATA': 0,
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_grid',
             '-l points -a invdistnn:power=2.0:smothing=0.0:radius=1.0:max_points=12:min_points=0:nodata=0.0 -ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])

    def testGridLinear(self):
        context = QgsProcessingContext()
        feedback = QgsProcessingFeedback()
        source = os.path.join(testDataPath, 'points.gml')
        alg = GridLinear()
        alg.initAlgorithm()

        # with no NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_grid',
             '-l points -a linear:radius=-1.0:nodata=0.0 -ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])
        # with NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'NODATA': 9999,
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_grid',
             '-l points -a linear:radius=-1.0:nodata=9999.0 -ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])
        # with "0" NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'NODATA': 0,
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_grid',
             '-l points -a linear:radius=-1.0:nodata=0.0 -ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])

    def testGridNearestNeighbour(self):
        context = QgsProcessingContext()
        feedback = QgsProcessingFeedback()
        source = os.path.join(testDataPath, 'points.gml')
        alg = GridNearestNeighbor()
        alg.initAlgorithm()

        # with no NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_grid',
             '-l points -a nearest:radius1=0.0:radius2=0.0:angle=0.0:nodata=0.0 -ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])
        # with NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'NODATA': 9999,
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_grid',
             '-l points -a nearest:radius1=0.0:radius2=0.0:angle=0.0:nodata=9999.0 -ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])
        # with "0" NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'NODATA': 0,
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_grid',
             '-l points -a nearest:radius1=0.0:radius2=0.0:angle=0.0:nodata=0.0 -ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])

    def testProximity(self):
        context = QgsProcessingContext()
        feedback = QgsProcessingFeedback()
        source = os.path.join(testDataPath, 'dem.tif')
        alg = proximity()
        alg.initAlgorithm()

        # with no NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'BAND': 1,
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_proximity.py',
             '-srcband 1 -distunits PIXEL -ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])
        # with NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'NODATA': 9999,
                                    'BAND': 2,
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_proximity.py',
             '-srcband 2 -distunits PIXEL -nodata 9999.0 -ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])
        # with "0" NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'NODATA': 0,
                                    'BAND': 1,
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_proximity.py',
             '-srcband 1 -distunits PIXEL -nodata 0.0 -ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])

    def testRasterize(self):
        context = QgsProcessingContext()
        feedback = QgsProcessingFeedback()
        source = os.path.join(testDataPath, 'polys.gml')
        alg = rasterize()
        alg.initAlgorithm()

        # with no NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'FIELD': 'id',
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_rasterize',
             '-l polys2 -a id -ts 0.0 0.0 -ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])
        # with NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'NODATA': 9999,
                                    'FIELD': 'id',
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_rasterize',
             '-l polys2 -a id -ts 0.0 0.0 -a_nodata 9999.0 -ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])
        # with "0" NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'NODATA': 0,
                                    'FIELD': 'id',
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdal_rasterize',
             '-l polys2 -a id -ts 0.0 0.0 -a_nodata 0.0 -ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])

    def testWarp(self):
        context = QgsProcessingContext()
        feedback = QgsProcessingFeedback()
        source = os.path.join(testDataPath, 'dem.tif')
        alg = warp()
        alg.initAlgorithm()

        # with no NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'CRS': 'EPSG:3111',
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdalwarp',
             '-t_srs EPSG:4326 -r near -ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])
        # with NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'NODATA': 9999,
                                    'CRS': 'EPSG:3111',
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdalwarp',
             '-t_srs EPSG:4326 -dstnodata 9999.0 -r near -ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])
        # with "0" NODATA value
        self.assertEqual(
            alg.getConsoleCommands({'INPUT': source,
                                    'NODATA': 0,
                                    'CRS': 'EPSG:3111',
                                    'OUTPUT': 'd:/temp/check.jpg'}, context, feedback),
            ['gdalwarp',
             '-t_srs EPSG:4326 -dstnodata 0.0 -r near -ot Float32 -of JPEG ' +
             source + ' ' +
             'd:/temp/check.jpg'])


class TestGdalOgrToPostGis(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # start_app()
        from processing.core.Processing import Processing
        Processing.initialize()

    @classmethod
    def tearDownClass(cls):
        pass

    # See https://issues.qgis.org/issues/15706
    def test_getConnectionString(self):
        obj = OgrToPostGis()
        obj.initAlgorithm({})

        parameters = {}
        context = QgsProcessingContext()

        # NOTE: defaults are debatable, see
        # https://github.com/qgis/QGIS/pull/3607#issuecomment-253971020
        self.assertEqual(obj.getConnectionString(parameters, context),
                         "host=localhost port=5432 active_schema=public")

        parameters['HOST'] = 'remote'
        self.assertEqual(obj.getConnectionString(parameters, context),
                         "host=remote port=5432 active_schema=public")

        parameters['HOST'] = ''
        self.assertEqual(obj.getConnectionString(parameters, context),
                         "port=5432 active_schema=public")

        parameters['PORT'] = '5555'
        self.assertEqual(obj.getConnectionString(parameters, context),
                         "port=5555 active_schema=public")

        parameters['PORT'] = ''
        self.assertEqual(obj.getConnectionString(parameters, context),
                         "active_schema=public")

        parameters['USER'] = 'usr'
        self.assertEqual(obj.getConnectionString(parameters, context),
                         "active_schema=public user=usr")

        parameters['PASSWORD'] = 'pwd'
        self.assertEqual(obj.getConnectionString(parameters, context),
                         "password=pwd active_schema=public user=usr")


if __name__ == '__main__':
    nose2.main()
