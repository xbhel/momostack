<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:math="http://www.w3.org/2005/xpath-functions/math"
    xmlns:fo="http://www.w3.org/1999/XSL/Format"
    exclude-result-prefixes="fo math xs">

    <!-- Declare parameters -->
    <xsl:param name="inputXml" />

    <!-- Declare gobale variables -->
    <xsl:variable name="sequence" select="1 to 5" />
    <xsl:variable name="fruits" select="('Apple', 'Banana', 'Cherry')" />
    <xsl:variable name="prices" select="(1.2, 2.3, 3.4)" />

    <xsl:template match="/">

        <!-- Declare variables -->
        <xsl:variable name="paramIndex" select="position()" />
        <xsl:variable name="paramName" select="/book/title" />

        <!-- Use variables -->
        <xsl:value-of select="$paramName" />  
        <xsl:value-of select="$paramIndex" />
        
        <!-- Use foreach -->
        <xsl:for-each select="$inputXml/parameters/entry">
            <td>
                <index>
                    <xsl:value-of select="position()" />
                </index>
                <text>
                    <xsl:value-of select="." />
                </text>
                <xsl:value-of select="@key" />
            </td>
        </xsl:for-each>
    
        <!-- Use xsl:apply-templates that is refered to a defined template for processing a list of elements. -->
        <xsl:apply-templates select="book/title" />

        <xsl:variable name="index" select="4" />
        <SequenceIndex>
            <!-- Index is a variable -->
            <xsl:for-each select="$inputXml/parameters/entry">
                <index> 
                    fixed index:
                    <xsl:value-of select="$sequence[$index]" /> 
                </index>
            </xsl:for-each>

            <xsl:for-each select="$inputXml/parameters/entry">
                <index>
                    <xsl:value-of select="position()" />
                    -
                    <xsl:value-of select="$prices[position()]" />
                </index>
            </xsl:for-each>
        </SequenceIndex>
        
        <output>
            <!-- Use xsl:for-each to iterate the fruits sequence -->
            <xsl:for-each select="$fruits">
                <item>
                    <fruit>
                        <xsl:value-of select="." />
                    </fruit>
                    <price>
                        <!-- 使用 position() 作为索引访问 prices 序列 -->
                        <xsl:value-of select="$prices[position()]" />
                    </price>
                </item>
            </xsl:for-each>
        </output>
    </xsl:template>

    <xsl:template match="title">
        <xsl:variable name="titlendex" select="position()" />
        <item>
            <index>
                <xsl:value-of select="position()" />
            </index>
            <value>
                <xsl:value-of select="." /> 
                position 
                <xsl:value-of select="$sequence[$titlendex]" />
            </value>
        </item>
    </xsl:template>

</xsl:stylesheet>