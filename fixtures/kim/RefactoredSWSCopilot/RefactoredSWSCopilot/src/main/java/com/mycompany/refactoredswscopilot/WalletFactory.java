/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredswscopilot;

/**
 *
 * @author kim2
 */
// Factory Method Pattern
abstract class WalletFactory {
    public abstract Wallet createWallet(String currency);
}

