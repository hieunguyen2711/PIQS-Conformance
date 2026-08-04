/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredswscopilot;

import java.util.HashMap;
import java.util.Map;

/**
 *
 * @author kim2
 */
// Singleton Pattern
class CurrencyConverter {
    private static final Map<String, Double> exchangeRates = new HashMap<>();

    static {
        exchangeRates.put("USD_EUR", 0.85);
        exchangeRates.put("EUR_USD", 1.17);
        // Add more exchange rates as needed
    }

    private CurrencyConverter() { 
        // private constructor
    }

    public static CurrencyConverter getInstance() {
        return Holder.INSTANCE;
    }

    private static class Holder {
        private static final CurrencyConverter INSTANCE = new CurrencyConverter();
    }

    public double convert(String fromCurrency, String toCurrency, double amount) {
        String key = fromCurrency + "_" + toCurrency;
        return amount * exchangeRates.getOrDefault(key, 1.0);
    }
}

