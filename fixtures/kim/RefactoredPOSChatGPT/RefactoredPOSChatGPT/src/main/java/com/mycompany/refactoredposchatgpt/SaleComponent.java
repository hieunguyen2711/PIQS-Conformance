/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposchatgpt;

/**
 *
 * @author kim2
 */
// Composite Pattern: Component
abstract class SaleComponent {
    public abstract double getSubTotal();
    public abstract void display();
}