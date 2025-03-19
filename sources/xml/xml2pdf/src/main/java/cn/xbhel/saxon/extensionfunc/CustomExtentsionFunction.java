package cn.xbhel.saxon.extensionfunc;

import java.util.Arrays;
import java.util.stream.Stream;

import lombok.extern.slf4j.Slf4j;
import net.sf.saxon.s9api.ExtensionFunction;
import net.sf.saxon.s9api.ItemType;
import net.sf.saxon.s9api.OccurrenceIndicator;
import net.sf.saxon.s9api.QName;
import net.sf.saxon.s9api.SaxonApiException;
import net.sf.saxon.s9api.SequenceType;
import net.sf.saxon.s9api.XdmAtomicValue;
import net.sf.saxon.s9api.XdmValue;

/**
 * Saxon-<a href=
 * "https://www.saxonica.com/documentation12/index.html#!extensibility/extension-functions-J">Writing
 * extension functions in Java.</a>
 */
@Slf4j
public class CustomExtentsionFunction implements ExtensionFunction {

    @Override
    public QName getName() {
        // namespace & function-name
        return new QName("http://www.example.com", "test");
    }

    @Override
    public SequenceType getResultType() {
        return SequenceType.makeSequenceType(ItemType.STRING, OccurrenceIndicator.ONE);
    }

    @Override
    public SequenceType[] getArgumentTypes() {
        return new SequenceType[] { SequenceType.ANY };
    }

    @Override
    public XdmValue call(XdmValue[] arguments) throws SaxonApiException {
        var args = Arrays.stream(arguments).map(XdmValue::toString).toList();
        // arguments: [<title id="1">1</title>]
        log.info("arguments: {}", args);

        var result = "Saxon is being extended correctly.";
        return new XdmAtomicValue(result);
    }

}
