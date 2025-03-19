package cn.xbhel.saxon.parameter;

import java.io.StringReader;

import javax.xml.transform.stream.StreamSource;

import cn.hutool.core.io.resource.ResourceUtil;
import net.sf.saxon.s9api.DocumentBuilder;
import net.sf.saxon.s9api.Processor;
import net.sf.saxon.s9api.QName;
import net.sf.saxon.s9api.SaxonApiException;
import net.sf.saxon.s9api.Serializer;
import net.sf.saxon.s9api.XdmNode;
import net.sf.saxon.s9api.XsltCompiler;
import net.sf.saxon.s9api.XsltExecutable;
import net.sf.saxon.s9api.XsltTransformer;

public class ParameterMain {
     public static void main(String[] args) throws SaxonApiException {
        Processor processor = new Processor(false);
        XsltCompiler compiler = processor.newXsltCompiler();
        var xslt = ResourceUtil.getStream("parameter.xsl");
        XsltExecutable executable = compiler.compile(new StreamSource(xslt));

        Serializer serializer = processor.newSerializer(System.out);
        serializer.setOutputProperty(Serializer.Property.INDENT, "yes");
        
        XsltTransformer transformer = executable.load();
        transformer.setSource(new StreamSource(ResourceUtil.getStream("parameter.xml")));

        // convert Map to XML format due xslt 2.0 don't support the map function.
        String xmlParam = "<parameters><entry key='1'>Saxon Transformation</entry><entry key='2'>John Doe</entry></parameters>";
        DocumentBuilder builder = processor.newDocumentBuilder();
        XdmNode xmlNode = builder.build(new StreamSource(new StringReader(xmlParam)));

        // Pass above XML as a XSLT variable.
        transformer.setParameter(new QName("inputXml"), xmlNode);

        transformer.setDestination(serializer);
        transformer.transform();
    }
}
