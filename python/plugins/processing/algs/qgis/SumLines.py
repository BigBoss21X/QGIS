# -*- coding: utf-8 -*-

"""
***************************************************************************
    SumLines.py
    ---------------------
    Date                 : August 2012
    Copyright            : (C) 2012 by Victor Olaya
    Email                : volayaf at gmail dot com
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

__author__ = 'Victor Olaya'
__date__ = 'August 2012'
__copyright__ = '(C) 2012, Victor Olaya'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os

from qgis.PyQt.QtGui import QIcon

from qgis.core import QgsFeature, QgsGeometry, QgsFeatureRequest, QgsDistanceArea, QgsProcessingUtils

from processing.algs.qgis.QgisAlgorithm import QgisAlgorithm
from processing.core.parameters import ParameterVector
from processing.core.parameters import ParameterString
from processing.core.outputs import OutputVector
from processing.tools import dataobjects, vector

pluginPath = os.path.split(os.path.split(os.path.dirname(__file__))[0])[0]


class SumLines(QgisAlgorithm):

    LINES = 'LINES'
    POLYGONS = 'POLYGONS'
    LEN_FIELD = 'LEN_FIELD'
    COUNT_FIELD = 'COUNT_FIELD'
    OUTPUT = 'OUTPUT'

    def icon(self):
        return QIcon(os.path.join(pluginPath, 'images', 'ftools', 'sum_lines.png'))

    def group(self):
        return self.tr('Vector analysis tools')

    def __init__(self):
        super().__init__()
        self.addParameter(ParameterVector(self.LINES,
                                          self.tr('Lines'), [dataobjects.TYPE_VECTOR_LINE]))
        self.addParameter(ParameterVector(self.POLYGONS,
                                          self.tr('Polygons'), [dataobjects.TYPE_VECTOR_POLYGON]))
        self.addParameter(ParameterString(self.LEN_FIELD,
                                          self.tr('Lines length field name', 'LENGTH')))
        self.addParameter(ParameterString(self.COUNT_FIELD,
                                          self.tr('Lines count field name', 'COUNT')))

        self.addOutput(OutputVector(self.OUTPUT, self.tr('Line length'), datatype=[dataobjects.TYPE_VECTOR_POLYGON]))

    def name(self):
        return 'sumlinelengths'

    def displayName(self):
        return self.tr('Sum line lengths')

    def processAlgorithm(self, parameters, context, feedback):
        lineLayer = QgsProcessingUtils.mapLayerFromString(self.getParameterValue(self.LINES), context)
        polyLayer = QgsProcessingUtils.mapLayerFromString(self.getParameterValue(self.POLYGONS), context)
        lengthFieldName = self.getParameterValue(self.LEN_FIELD)
        countFieldName = self.getParameterValue(self.COUNT_FIELD)

        (idxLength, fieldList) = vector.findOrCreateField(polyLayer,
                                                          polyLayer.fields(), lengthFieldName)
        (idxCount, fieldList) = vector.findOrCreateField(polyLayer, fieldList,
                                                         countFieldName)

        writer = self.getOutputFromName(self.OUTPUT).getVectorWriter(fieldList, polyLayer.wkbType(),
                                                                     polyLayer.crs(), context)

        spatialIndex = QgsProcessingUtils.createSpatialIndex(lineLayer, context)

        ftLine = QgsFeature()
        ftPoly = QgsFeature()
        outFeat = QgsFeature()
        inGeom = QgsGeometry()
        outGeom = QgsGeometry()
        distArea = QgsDistanceArea()

        features = QgsProcessingUtils.getFeatures(polyLayer, context)
        total = 100.0 / QgsProcessingUtils.featureCount(polyLayer, context)
        hasIntersections = False
        for current, ftPoly in enumerate(features):
            inGeom = ftPoly.geometry()
            attrs = ftPoly.attributes()
            count = 0
            length = 0
            hasIntersections = False
            lines = spatialIndex.intersects(inGeom.boundingBox())
            engine = None
            if len(lines) > 0:
                hasIntersections = True
                # use prepared geometries for faster intersection tests
                engine = QgsGeometry.createGeometryEngine(inGeom.geometry())
                engine.prepareGeometry()

            if hasIntersections:
                request = QgsFeatureRequest().setFilterFids(lines).setSubsetOfAttributes([])
                for ftLine in lineLayer.getFeatures(request):
                    tmpGeom = ftLine.geometry()
                    if engine.intersects(tmpGeom.geometry()):
                        outGeom = inGeom.intersection(tmpGeom)
                        length += distArea.measureLength(outGeom)
                        count += 1

            outFeat.setGeometry(inGeom)
            if idxLength == len(attrs):
                attrs.append(length)
            else:
                attrs[idxLength] = length
            if idxCount == len(attrs):
                attrs.append(count)
            else:
                attrs[idxCount] = count
            outFeat.setAttributes(attrs)
            writer.addFeature(outFeat)

            feedback.setProgress(int(current * total))

        del writer
