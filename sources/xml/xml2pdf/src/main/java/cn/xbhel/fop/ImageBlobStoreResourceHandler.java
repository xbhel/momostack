package cn.xbhel.fop;

import java.io.IOException;
import java.net.URI;

import org.apache.xmlgraphics.io.Resource;

public class ImageBlobStoreResourceHandler implements BlobStoreResourceHandler {
    @Override
    public boolean isSupport(URI uri) {
        return uri.getScheme().equals("image");
    }

    @Override
    public Resource getResource(URI uri) throws IOException {
        throw new UnsupportedOperationException("Unimplemented method 'getResource'");
    }
 
}
