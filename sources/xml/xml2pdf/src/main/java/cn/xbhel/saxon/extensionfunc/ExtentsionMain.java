package cn.xbhel.saxon.extensionfunc;

import java.io.InputStream;

import javax.xml.transform.stream.StreamSource;

import cn.hutool.core.io.resource.ResourceUtil;
import net.sf.saxon.s9api.Processor;
import net.sf.saxon.s9api.SaxonApiException;
import net.sf.saxon.s9api.Serializer;
import net.sf.saxon.s9api.XsltCompiler;
import net.sf.saxon.s9api.XsltExecutable;
import net.sf.saxon.s9api.XsltTransformer;

public class ExtentsionMain {
    public static void main(String[] args) throws SaxonApiException {
        Processor processor = new Processor(false);
        XsltCompiler compiler = processor.newXsltCompiler();
        processor.registerExtensionFunction(new CustomExtentsionFunction());
        InputStream xslt = ResourceUtil.getStream("extension.xsl");
        XsltExecutable executable = compiler.compile(new StreamSource(xslt));
        XsltTransformer transformer = executable.load();
        Serializer serializer = processor.newSerializer(System.out);
        serializer.setOutputProperty(Serializer.Property.INDENT, "yes");
        transformer.setSource(new StreamSource(ResourceUtil.getStream("extension.xml")));
        transformer.setDestination(serializer);
        transformer.transform();
    }
}
