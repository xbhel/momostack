package cn.xbhel.fop;

import java.io.IOException;
import java.io.OutputStream;
import java.net.URI;

import org.apache.xmlgraphics.io.Resource;


public interface BlobStoreResourceHandler {
    
    boolean isSupport(URI uri);

    Resource getResource(URI uri) throws IOException;

    default OutputStream getOutputStream(URI uri) throws IOException {
        throw new UnsupportedOperationException("Not supported");
    }

}
