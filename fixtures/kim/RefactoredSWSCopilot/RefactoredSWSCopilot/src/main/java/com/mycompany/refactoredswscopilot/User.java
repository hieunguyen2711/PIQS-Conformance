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
class User {
    private String name;
    private String password;
    private Map<String, Wallet> wallets;
    private AuditLog auditLog;
    private WalletFactory walletFactory;

    public User(String name, String password, WalletFactory walletFactory) {
        this.name = name;
        this.password = password;
        this.wallets = new HashMap<>();
        this.auditLog = new AuditLog();
        this.walletFactory = walletFactory;
        auditLog.logAction("User created: " + name);
    }

    public boolean authenticate(String password) {
        return this.password.equals(password);
    }

    // Factory Method Pattern
    public void addWallet(String currency) {
        if (!wallets.containsKey(currency)) {
            Wallet wallet = walletFactory.createWallet(currency);
            wallets.put(currency, wallet);
            auditLog.logAction("Wallet added: " + currency);
            wallet.addObserver(auditLog);
        }
    }

    public Wallet getWallet(String currency) {
        return wallets.get(currency);
    }

    public void showAllBalances() {
        wallets.forEach((currency, wallet) -> {
            wallet.showBalance();
        });
    }
}
