/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredswsclaude;

import java.util.HashMap;
import java.util.Map;

/**
 *
 * @author kim2
 */
// -------------------- Singleton Pattern Start --------------------
class CurrencyConverter {
    private static CurrencyConverter instance;
    private final Map<String, Double> exchangeRates;

    private CurrencyConverter() {
        exchangeRates = new HashMap<>();
        exchangeRates.put("USD_EUR", 0.85);
        exchangeRates.put("EUR_USD", 1.17);
    }

    public static synchronized CurrencyConverter getInstance() {
        if (instance == null) {
            instance = new CurrencyConverter();
        }
        return instance;
    }

    public double convert(String fromCurrency, String toCurrency, double amount) {
        String key = fromCurrency + "_" + toCurrency;
        return amount * exchangeRates.getOrDefault(key, 1.0);
    }
}
// -------------------- Singleton Pattern End --------------------
