package cn.xbhel;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;

import javax.xml.transform.TransformerFactory;
import javax.xml.transform.sax.SAXResult;
import javax.xml.transform.stream.StreamSource;

import org.apache.commons.io.IOUtils;
import org.apache.fop.apps.FopFactory;
import org.apache.xmlgraphics.util.MimeConstants;

import cn.hutool.core.lang.Assert;
import net.sf.saxon.TransformerFactoryImpl;

public class PdfGenerator {

    private final FopFactory fopFactory;

    public PdfGenerator() {
        this.fopFactory = FopFactory.newInstance(Path.of(".").toUri());
    }

    void generate(InputStream input, InputStream xslt, OutputStream output) throws Exception {
        Assert.notNull(input, "The input is required.");
        Assert.notNull(input, "The xslt is required.");
        Assert.notNull(input, "The output is required.");

        try (input; xslt; output) {
            var source = new StreamSource(input);
            var transformSource = new StreamSource(xslt);
            var userAgent = fopFactory.newFOUserAgent();
            var transformFactory = TransformerFactory.newInstance(
                    TransformerFactoryImpl.class.getCanonicalName(), null);
            var transformer = transformFactory.newTransformer(transformSource);
            var fop = fopFactory.newFop(MimeConstants.MIME_PDF, userAgent, output);
            var result = new SAXResult(fop.getDefaultHandler());
            transformer.transform(source, result);
        }
    }

    OutputStream generate(String xmlSource, InputStream xslt) throws Exception {
        var output = new ByteArrayOutputStream();
        generate(
                IOUtils.toInputStream(xmlSource, StandardCharsets.UTF_8),
                xslt,
                output);

        return output;
    }

}
