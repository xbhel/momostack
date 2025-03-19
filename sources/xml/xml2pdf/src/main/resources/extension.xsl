<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:math="http://www.w3.org/2005/xpath-functions/math"
    xmlns:fo="http://www.w3.org/1999/XSL/Format"
    xmlns:ext="http://www.example.com"
    exclude-result-prefixes="fo math xs">

    <xsl:template match="title">
        <item>
            <index>
                <xsl:value-of select="concat(@id, .)" />
            </index>
            <value>
                <xsl:value-of select="ext:test(.)" />
            </value>
        </item>
    </xsl:template>

</xsl:stylesheet>