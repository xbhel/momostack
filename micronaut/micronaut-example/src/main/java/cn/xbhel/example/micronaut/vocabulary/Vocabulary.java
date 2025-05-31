package cn.xbhel.example.micronaut.vocabulary;

import lombok.Data;

/**
 * Aggregate Root
 */
@Data
public class Vocabulary {
    private String word;
    private String meaning;
    private String example;
    private String sentence;
    private String sentenceMeaning;
    private String sentenceExample;
    private String sentenceSentence;
}
