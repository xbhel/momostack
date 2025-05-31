package cn.xbhel.example.micronaut.vocabulary;

import java.net.http.HttpResponse;

import io.micronaut.http.annotation.Controller;
import io.micronaut.http.annotation.Get;

/**
 * Controller protocol layer
 */
@Controller("/vocabulary")
public class VocabularyController {

    @Get("/{word}")
    public HttpResponse<String> get(@PathVariable String word) {
        // Utilize the dictionaries recommended in "Learn English Grammar Like a Professional" to enhance your English grammar skills
        return HttpResponse.ok(word);
    }
}
