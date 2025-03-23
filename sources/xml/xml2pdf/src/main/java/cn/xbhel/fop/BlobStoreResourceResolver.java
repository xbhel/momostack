package cn.xbhel.fop;

import java.io.IOException;
import java.io.OutputStream;
import java.net.URI;
import java.util.ArrayList;
import java.util.List;

import org.apache.fop.apps.io.ResourceResolverFactory;
import org.apache.xmlgraphics.io.Resource;
import org.apache.xmlgraphics.io.ResourceResolver;

public class BlobStoreResourceResolver implements ResourceResolver {

    private static final String BLOB_STORE_SCHEMA = "blobstore";

    private final ResourceResolver delegate;
    private final List<BlobStoreResourceHandler> handlers = new ArrayList<>();

    public BlobStoreResourceResolver() {
        this.delegate = ResourceResolverFactory.createDefaultResourceResolver();
    }

    @Override
    public Resource getResource(URI uri) throws IOException {
        if (!isBlobStoreURI(uri)) {
            return delegate.getResource(uri);
        }
        for (BlobStoreResourceHandler handler : handlers) {
            if (handler.isSupport(uri)) {
                return handler.getResource(uri);
            }
        }
        throw new IOException("No handler found for URI: " + uri);
    }

    @Override
    public OutputStream getOutputStream(URI uri) throws IOException {
        if (!isBlobStoreURI(uri)) {
            return delegate.getOutputStream(uri);
        }
        for (BlobStoreResourceHandler handler : handlers) {
            if (handler.isSupport(uri)) {
                return handler.getOutputStream(uri);
            }
        }
        throw new IOException("No handler found for URI: " + uri);
    }

    public void setHandlers(List<BlobStoreResourceHandler> handlers) {
        this.handlers.clear();
        this.handlers.addAll(handlers);
    }

    public BlobStoreResourceResolver addHandler(BlobStoreResourceHandler handler) {
        handlers.add(handler);
        return this;
    }

    boolean isBlobStoreURI(URI uri) {
        return BLOB_STORE_SCHEMA.equals(uri.getScheme());
    }

}
